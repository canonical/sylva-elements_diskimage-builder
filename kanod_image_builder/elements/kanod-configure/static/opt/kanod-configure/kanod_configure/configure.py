#  Copyright (C) 2020-2021 Orange
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64
import hashlib
import importlib
import os
from os import path
import requests
import socket
import sys
import tempfile
import time
from typing import Any, Callable, Dict  # noqa: H301

from cloudinit.distros import rhel, opensuse  # noqa: F401
from cloudinit.net import netplan
from cloudinit.net import network_manager
from cloudinit.net import sysconfig
from cloudinit import stages
from cloudinit import subp
from cloudinit import util
import yaml

from . import common
from . import util_opensuse
from . import includes  # noqa: F401

DEFAULT_NO_PROXY = (
    'localhost,127.0.0.1,10.96.0.0/16,192.168.0.0/16,127.0.0.1,localhost,'
    '.svc,.local,argocd-repo-server')

configuration_table: Dict[str, Callable[[stages.Init, Any, Any], None]] = {}


def complete_no_proxy(sys, no_proxy):
    '''Complete no_proxy with kanod values

    Some ip and domains MUST NOT go through the proxy (mainly internal pod)
    '''
    elements = no_proxy.split(',')
    sys_proxy = sys.get('no_proxy', DEFAULT_NO_PROXY)
    added_proxy = [elt for elt in sys_proxy.split(',') if elt not in elements]
    return ','.join(elements + added_proxy)


def setup_certificates(conf):
    '''Update the certificates of the system'''
    if path.exists('/usr/local/share/ca-certificates'):
        target = path.join('/usr/local/share/ca-certificates', 'kanod')
        common.setup_certificates(conf, target, suffix='.crt')
        subp.subp(['update-ca-certificates'])
    elif path.exists('/etc/pki/ca-trust/source/anchors/'):
        target = '/etc/pki/ca-trust/source/anchors/'
        common.setup_certificates(conf, target, suffix='.crt')
        subp.subp(['update-ca-trust'])
    elif path.exists('/usr/share/pki/trust/anchors'):
        target = '/usr/share/pki/trust/anchors'
        common.setup_certificates(conf, target, suffix='.crt')
        subp.subp(['update-ca-certificates'])
    else:
        print('Cannot handle certificates on this system.')


def setup_proxy(sys, conf):
    '''Configure the proxy variables'''
    proxy_vars = conf.get('proxy')
    if proxy_vars is not None:
        no_proxy = proxy_vars.get('no_proxy', None)
        if no_proxy is not None:
            proxy_vars['no_proxy'] = complete_no_proxy(sys, no_proxy)
        print('Configure proxy (base)')
        common.render_template(
            'environment.tmpl', 'etc/environment', proxy_vars)
        common.propagate_var(proxy_vars, 'http', 'http_proxy')
        common.propagate_var(proxy_vars, 'https', 'https_proxy')
        common.propagate_var(proxy_vars, 'no_proxy', 'no_proxy')


def wait_for_vault(vault_url, verify):
    while True:
        try:
            req = requests.get(f'{vault_url}/v1/sys/health', verify=verify)
            if req.status_code == 200:
                if not req.json().get('sealed', True):
                    break
                else:
                    print('Vault sealed')
            else:
                print('Error connecting to Vault')
        except Exception as e:
            print(f'cannot reach Vault: {e}')
        time.sleep(5)


def tpm_sign(context):
    with tempfile.TemporaryDirectory() as tmpdir:
        for file in [
            'key.ctxt', 'key.priv', 'key.pub'
        ]:
            with open(path.join(tmpdir, file), 'wb') as fd:
                content = context.get(file, None)
                if content is None:
                    raise Exception(f'component {file} not found')
                fd.write(base64.b64decode(content.encode('ascii')))
        print('- recreating primary context')
        command = [
            'tpm2', 'createprimary', '-G', 'rsa',
            '-c', f'{tmpdir}/primary.ctxt']
        subp.subp(command)
        print('- trying to recover TPM secundary key')
        command = [
            'tpm2', 'load', '-C', f'{tmpdir}/primary.ctxt',
            '-c', f'{tmpdir}/key.ctxt', '-u', f'{tmpdir}/key.pub',
            '-r', f'{tmpdir}/key.priv']
        subp.subp(command)
        command = [
            'md5sum', f'{tmpdir}/primary.ctxt', f'{tmpdir}/key.ctxt',
            f'{tmpdir}/key.pub', f'{tmpdir}/key.priv']
        subp.subp(command)
        print('- writing digest')
        nonce = context.get('nonce', None)
        m = hashlib.sha256()
        m.update(nonce.encode('utf-8'))
        with open(path.join(tmpdir, 'digest'), 'wb') as fd:
            fd.write(m.digest())
        print('- signing nonce digest')
        command = [
            'tpm2', 'sign', '-c', f'{tmpdir}/key.ctxt', '-g', 'sha256', '-o',
            f'{tmpdir}/sign.raw', '-f', 'plain', '-d', f'{tmpdir}/digest'
        ]
        subp.subp(command)
        with open(path.join(tmpdir, 'sign.raw'), 'rb') as fd:
            sign = base64.b64encode(fd.read()).decode('ascii')
    return sign


def make_verify(opt_ca):
    '''Define the verify argument for https connection.

    If a CA is provided, use it (dump the value to a file and return the file
    name), otherwise force verify and assume the certificate is in the
    default store.
    '''
    if opt_ca is None:
        verify = True
    else:
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, encoding='utf-8'
        ) as fd:
            fd.write(opt_ca)
            fd.write('\n')
            verify = fd.name
    return verify


def vault_authenticate(name, vault_url, verify, vault_conf):
    vault_role_id = vault_conf.get('role_id', None)
    gatekeeper_url = vault_conf.get('tpm_auth', None)
    if gatekeeper_url is not None:
        print('- use the gatekeeper to get a token')
        tpm_auth_ca = vault_conf.get('tpm_auth_ca', None)
        verify_gk = make_verify(tpm_auth_ca)
        req = requests.get(
            f'{gatekeeper_url}/challenge',
            params={'name': name},
            verify=verify_gk
        )
        if req.status_code != 200:
            raise Exception(f'Cannot get a challenge ({req.status_code})')
        print('- got a challenge')
        context = req.json()
        signature = tpm_sign(context)
        req = requests.get(
            f'{gatekeeper_url}/secret_id',
            params={'name': name, 'signature': signature},
            verify=verify_gk
        )
        if req.status_code != 200:
            raise Exception(
                f'Signature verification failed ({req.status_code})')
        print('- extracting secret-id from gatekeeper answer')
        vault_secret = req.json().get('data')
    else:
        print('- secret-id from config')
        vault_secret = vault_conf.get('secret_id', None)
    if vault_role_id is not None and vault_secret is not None:
        print('- Computing the token')
        req = requests.post(
            f'{vault_url}/v1/auth/approle/login',
            json={'role_id': vault_role_id, 'secret_id': vault_secret},
            verify=verify
        )

        if req.status_code == 200:
            vault_token = req.json().get('auth', {}).get('client_token', None)
            return vault_token
        else:
            raise Exception(
                f'AppRole auth failed - no token ({req.status_code})')
    raise Exception('Cannot proceed with vault')


def vault_config(arg: common.RunnableParams):
    conf = arg.conf
    name = conf.get('name', None)
    vault_conf = conf.get('vault', None)
    if vault_conf is None:
        return
    vault_ca = vault_conf.get('ca', None)
    verify = make_verify(vault_ca)
    vault_url = vault_conf.get('url', None)
    vault_role = vault_conf.get('role', None)
    try:
        vault_token = vault_authenticate(name, vault_url, verify, vault_conf)
    except Exception as e:
        print(e)
        return
    certs = {}
    vault_certs = vault_conf.get('certificates', [])
    print('- Adding certificates')
    for vault_cert in vault_certs:
        name = vault_cert.get('name', None)
        role = vault_cert.get('role', vault_role)
        ip = vault_cert.get('ip', None)
        alt = vault_cert.get('alt_names', None)
        print(f'Generating certificate {name}')
        json = {'common_name': name}
        if ip is not None:
            json['ip_sans'] = ','.join(ip)
        if alt is not None:
            json['alt_names'] = ','.join(alt)
        req = requests.post(
            f'{vault_url}/v1/pki/issue/{role}',
            headers={'X-Vault-Token': vault_token},
            json=json, verify=verify
        )
        if req.status_code != 200:
            print(
                f'Failed to generate certificate {name} '
                f'({req.status_code}): {req.content.decode("utf-8")}')
            continue
        data = req.json().get('data', {})
        cert = data.get('certificate', None)
        key = data.get('private_key', None)
        ca_chain = data.get('ca_chain', None)
        if cert is None or key is None or ca_chain is None:
            print(f'Something wrong during generation of cert {name}')
            continue
        certs[name] = (key, cert, ca_chain)

    def vault_transformer(val):
        if isinstance(val, str) and val.startswith('@vault:'):
            vault_entities = val.split(':', 2)
            l_ent = len(vault_entities)
            if l_ent < 2:
                raise Exception('malformed vault reference')
            vault_type = vault_entities[1]
            if vault_type == 'kv1' and l_ent == 3:
                args = vault_entities[2].split(':')
                if len(args) < 2:
                    raise Exception('not enough arguments for kv1')
                vault_path = args[0]
                vault_key = args[1]
                subpath = path.normpath(
                    path.join('secret', vault_role, vault_path))
                req = requests.get(
                    f'{vault_url}/v1/{subpath}',
                    headers={'X-Vault-Token': vault_token}, verify=verify
                )
                if req.status_code == 200:
                    res = req.json().get('data', {}).get(vault_key, None)
                    return res
                else:
                    print(f'Rendering {val}: wrong status {req.status_code}')
            elif vault_type == 'kv2' and l_ent == 3:
                args = vault_entities[2].split(':')
                if len(args) < 2:
                    raise Exception('not enough arguments for kv2')
                vault_path = vault_entities[0]
                vault_key = vault_entities[1]
                subpath = path.normpath(
                    path.join('kv', vault_role, vault_path))
                req = requests.get(
                    f'{vault_url}/v1/{subpath}',
                    headers={'X-Vault-Token': vault_token}, verify=verify
                )
                if req.status_code == 200:
                    cell = req.json().get('data', {}).get('data', {})
                    res = cell.get(vault_key, None)
                    return res
                else:
                    print(f'Rendering {val}: wrong status {req.status_code}')
            elif vault_type == 'pki-key' and l_ent == 3:
                res = certs.get(vault_entities[2], (None, None, None))[0]
                if res is not None:
                    return res
                else:
                    print(f'could not find translation for {val}')
            elif vault_type == 'pki-cert' and l_ent == 3:
                res = certs.get(vault_entities[2], (None, None, None))[1]
                if res is not None:
                    return res
                else:
                    print(f'could not find translation for {val}')
            elif vault_type == 'pki-ca-chain' and l_ent == 3:
                res = certs.get(vault_entities[2], (None, None, None))[2]
                if res is not None:
                    return res
                else:
                    print(f'could not find translation for {val}')
            elif vault_type == 'pki-chain' and l_ent == 3:
                (key, cert, chain) = certs.get(
                    vault_entities[2], (None, None, None))
                if cert is not None and chain is not None:
                    return cert + '\n' + '\n'.join(chain)
                else:
                    print(f'could not find translation for {val}')
            # Note: pki/ca gives only the intermediate ca. This is not what
            # curl or python requests expect. In ca_chain we are usually only
            # interested in the last certificate (real root)
            elif vault_type == 'ca' and l_ent == 2:
                req = requests.get(
                    f'{vault_url}/v1/pki/ca_chain',
                    verify=verify)
                if req.status_code == 200:
                    return req.content.decode('utf-8')
                else:
                    print('Cannot fetch the CA certificate')
            elif vault_type == 'yaml' and l_ent == 3:
                yml = list(yaml.safe_load_all(vault_entities[2]))
                common.transform_json(yml, vault_transformer)
                translated_arg = yaml.safe_dump_all(yml)
                return translated_arg
            else:
                print(f'unknown vault request type: {vault_type}')
        return None
    arg.system['vault_save'] = {
        'vault_url': vault_url,
        'vault_token': vault_token,
        'vault_verify': verify
    }
    common.transform_json(conf, vault_transformer)


common.register('Vault configuration', 70, vault_config)


def base_config(arg: common.RunnableParams):
    '''Setup variables, proxys and certificates'''
    os.environ['HOME'] = '/root'
    setup_proxy(arg.system, arg.conf)
    setup_certificates(arg.conf)


common.register('Base_config', 50, base_config)


def check_network(spec, iter):
    url = spec.get('http', None)
    if url is not None:
        try:
            print(f'check url {url} - {iter}')
            timeout=float(spec.get('timeout', 5))
            requests.head(url, timeout=timeout)
            return True
        except Exception:
            return False
    tcp = spec.get('tcp', None)
    if tcp is not None:
        components = tcp.split(':')
        if len(components) == 2:
            addr = components[0]
            port = int(components[1])
            print(f'check tcp connection {addr}:{port} - {iter}')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.settimeout(10)
                sock.connect((addr, port))
                return True
            except Exception:
                return False
            finally:
                sock.close()
        else:
            return False
    dns = spec.get('dns', None)
    if dns is not None:
        try:
            print(f'check address {dns} - {iter}')
            socket.getaddrinfo(dns, 0)
            return True
        except Exception:
            return False
    return False


def network_config(arg: common.RunnableParams):
    nmcli_path = '/bin/nmcli'
    conf = arg.conf
    distro = arg.init.distro
    print('Extract network state')
    state = conf.get('network')
    if state is None:
        print('Network not configured')
        return

    # Opensuse
    if isinstance(distro, opensuse.Distro):
        nmcli_path = '/usr/bin/nmcli'
        subp.subp(['rm', '-f', '/etc/resolv.conf'])

    # Prepare rendering. Enable networkManager (not done before start-up
    # or it hangs)
    bring_up = True
    if path.exists(nmcli_path):
        bring_up = False
        print('Enable NetworkManager service')
        subp.subp(['systemctl', 'enable', 'NetworkManager'])

    print('Rendering state')
    if not distro.apply_network_config(state, bring_up=bring_up):
        print('Failed to render config')

    # Post rendering: enable networking on NetworkManager
    if path.exists(nmcli_path):
        print('Start NetworkManager service')
        subp.subp(['systemctl', 'start', 'NetworkManager'])

    checks = conf.get('network_checks', [])
    for check in checks:
        iter = 0
        max_tries = check.get('tries', -1)
        while not check_network(check, iter) and iter != max_tries:
            time.sleep(2)
            iter += 1

common.register('Network configuration', 10, network_config)


class Unbuffered(object):
    '''A small class to force flushing on  a stream'''

    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


def initialize():
    sys.stdout = Unbuffered(sys.stdout)
    init = stages.Init()
    print('Reading configuration')
    conf = util.read_conf(common.USER_CONF)
    if path.exists(common.SYSTEM_CONF):
        system = util.read_conf(common.SYSTEM_CONF)
    else:
        system = {}
    libraries = system.get('libraries') or []
    for library in libraries:
        mod = importlib.import_module(library)
        mod.init()
    return (init, conf, system)


def write_status(n):
    target = path.join(common.ROOT, 'etc/kanod-configure/status')
    with open(target, 'w') as fd:
        fd.write(str(n))


def main():
    print('Starting kanod-runcmd')
    (init, conf, system) = initialize()
    min = None if len(sys.argv) < 2 else int(sys.argv[1])
    try:
        common.run(common.RunnableParams(init, conf, system), min=min)
        write_status(0)
    except Exception as e:
        write_status(1)
        print(e)


if __name__ == '__main__':
    main()

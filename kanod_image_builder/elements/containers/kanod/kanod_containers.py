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
import pathlib
import urllib.parse as urlparse

from kanod_configure import common

def strip_scheme(url):
    if url.startswith('http://'):
        return url[7:]
    elif url.startswith('https://'):
        return url[8:]
    else:
        return url


def find_registry_server(servers, url):
    server = next(
        filter(lambda x: x.get('url', None) == url, servers),
        None)
    if server is None:
        server = {'url': url, 'shortname': urlparse.urlparse(url).netloc}
        servers.append(server)
    return server


def find_registry_config(map, name):
    config = next(
        filter(lambda x: x.get('name', None) == name, map),
        None)
    if config is None:
        config = {'name': name}
        map.append(config)
    return config


def translate_registries(args: common.RunnableParams):
    conf = args.conf
    new_registries = conf.setdefault('container_registries', {})
    servers = new_registries.setdefault('servers', [])
    map = new_registries.setdefault('map', [])
    for server in servers:
        server['shortname'] = urlparse.urlparse(server.get('url','')).netloc
    docker_cfg = find_registry_config(map, 'docker.io')
    docker_cfg['server'] = 'https://registry-1.docker.io'
    old_registries = conf.get('containers', None)
    if old_registries is not None:
        # Copy insecure status information
        for insec_reg in old_registries.get('insecure_registries', []):
            url = f'https://{insec_reg}'
            server = find_registry_server(servers, url)
            server['insecure'] = True
            config = find_registry_config(map, insec_reg)
            config['server'] = f'http://{insec_reg}'
            mirrors = config.setdefault('mirrors', [])
            mirrors.append(url)

        # Copy auth informations.
        for auth_reg in old_registries.get('auths', []):
            url = f"https://{auth_reg['repository']}"
            server = find_registry_server(servers, url)
            server['username'] = auth_reg['username']
            server['password'] = auth_reg['password']

        # Copy default mirrors. Not supported by cri-o
        mirrors = old_registries.get('registry_mirrors', None)
        if mirrors is not None:
            new_registries['default_mirrors'] = (
                new_registries.get('default_mirrors', []) + mirrors)

        # This step ensures that no configuration is done on the old format
        # and that the field is really deprecated.
        del conf['containers']


common.register('-> old format registry hook', 50, translate_registries)


ROOT_CERTIFICATES = '/etc/containers/certs.d'

def certificates(servers):
    '''Dump certificates for container engines

    This is used by both crio (default hierarchy) and containerd (Kanod
    design decision)
    '''
    for server in servers:
        for field, filename in [
            ('ca', 'ca.crt'),
            ('client_cert', 'client.cert'),
            ('client_key', 'client.key')
        ]:
            if field in server:
                folder = pathlib.Path(ROOT_CERTIFICATES, server['shortname'])
                folder.mkdir(parents=True, exist_ok=True)
                file = folder.joinpath(filename)
                with open(file, 'w', encoding='utf-8') as fd:
                    fd.write(server[field])
                    fd.write('\n')

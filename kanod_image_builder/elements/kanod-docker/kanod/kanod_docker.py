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


from cloudinit import subp

from kanod_configure import common

from . import kanod_containers


def set_docker_auth(conf):
    '''Set authentication tokens for private registries'''
    containers_vars = conf.get('container_registries', {})
    raw_auths = containers_vars.get('servers', None)
    # first destination for docker stand-alone, second for used as kubelet
    # engine
    destination = (
        'root/.docker/config.json' if 'kubernetes' in conf
        else 'var/lib/kubelet/config.json')
    if raw_auths is None:
        return
    auths = [
        {
            "repo": kanod_containers.strip_scheme(cell.get('url', '')),
            "token": common.b64(
                cell['username'] + ':' + cell.get('password', '')),
        }
        for cell in raw_auths
        if 'username' in cell
    ]
    common.render_template(
        'dockercfg.tmpl',
        destination,
        {'auths': auths}
    )


def container_engine_docker_config(conf):
    '''Configure the docker container engine'''
    proxy_vars = conf.get('proxy')
    if proxy_vars is not None:
        common.render_template(
            'container_engine_proxy.tmpl',
            'etc/systemd/system/docker.service.d/http-proxy.conf',
            proxy_vars
        )

    servers = conf['container_registries']['servers']
    insecure_registries = [
        kanod_containers.strip_scheme(server.get('url')) for server in servers
        if server.get('insecure', False) or server.get('url').startswith('http:')]
    map = conf['container_registries']['map']
    docker_conf = kanod_containers.find_registry_config(map, 'docker.io')
    mirrors = conf['container_registries'].get('default_mirrors', [])
    common.render_template(
        'docker_daemon.tmpl',
        'etc/docker/daemon.json',
        {'insecure_registries': insecure_registries,
         'registry_mirrors': mirrors}
    )
    set_docker_auth(conf)
    subp.subp(['systemctl', 'daemon-reload'])
    subp.subp(['systemctl', 'enable', 'docker'])
    subp.subp(['systemctl', 'start', 'docker'])


def register_docker_engine(arg: common.RunnableParams):
    engines = arg.system.setdefault('container-engines', {})
    engines['docker'] = container_engine_docker_config


common.register('Register docker engine', 80, register_docker_engine)

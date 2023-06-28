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

from kanod_configure import common
from . import kanod_containers

KANOD_GITLAB_REGISTRY = 'https://registry.gitlab.com/orange-opensource/kanod'


def nexus_hook(arg: common.RunnableParams):
    conf = arg.conf
    nexus = conf.get('nexus', {})
    map = conf['container_registries']['map']
    nexus_registry = nexus.get('docker', None)
    if nexus_registry is not None:
        insecure = nexus.get('insecure', False)
        schema = 'http' if insecure else 'https'
        url = f'{schema}://{nexus_registry}'
        servers = conf['container_registries']['servers']
        server = kanod_containers.find_registry_server(servers, url)
        if insecure:
            server['insecure'] = True
        for target in [
            'registry.gitlab.com', 'quay.io', 'k8s.gcr.io',  'registry.k8s.io',
            'gcr.io', 'ghcr.io', 'docker.io'
        ]:
            config = kanod_containers.find_registry_config(map, target)
            mirrors = config.setdefault('mirrors', [])
            mirrors.append(url)
        config['server'] = url
        config['mirrors'] = [url]
        if 'certificate' in nexus:
            server['ca'] = nexus['certificate']

common.register('-> Nexus hook', 149, nexus_hook)

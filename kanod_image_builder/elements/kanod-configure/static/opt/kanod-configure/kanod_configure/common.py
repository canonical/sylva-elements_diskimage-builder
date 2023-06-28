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
import os
from os import path
import pkg_resources
from typing import Any, Callable, Dict, List, NamedTuple, Optional  # noqa: H301,E501

from cloudinit import stages
from cloudinit import templater

ROOT = '/'
SYSTEM_CONF = '/etc/kanod-configure/system.yaml'
USER_CONF = '/etc/kanod-configure/configuration.yaml'
MARK_FILE = '/var/lib/kanod-boot-once'


def render_template(name, target_path, vars, resource_package=__name__):
    '''Render a template located in template folder

    :param name: name of the template in the template folder
    :param path: path on the target file system where the template must
        be expanded
    :param vars: context dictionary to customize the template
    :param resource_package: name of resource package on which to base the
       lookup for the template.
    '''
    template_path = '/'.join(['templates', name])
    content = pkg_resources.resource_string(resource_package, template_path)
    templater.render_string_to_file(
        content.decode('utf-8'),
        path.join(ROOT, target_path),
        vars)


def propagate_var(conf, conf_var, system_var):
    '''Take a variable from a conf file and makes it an environment variable

    :param conf: the configuration the variable belongs to
    :param conf_var: the conf variable name
    :param env_var: the env variable name
    '''
    val = conf.get(conf_var, None)
    if val is not None:
        os.environ[system_var] = val


def setup_certificates(config, cert_folder, suffix=None):
    '''Extract certificates from configuration and write them as files.

    :param config: source configuration (was a yaml file)
    :param cert_folder: target folder for certificates
    '''
    certificates = config.get('certificates', {})
    if not path.exists(cert_folder):
        os.mkdir(cert_folder)
    for (cert_name, cert_value) in certificates.items():
        full_name = cert_name if suffix is None else cert_name + suffix
        with open(path.join(cert_folder, full_name), 'w') as fd:
            fd.write(cert_value)
            fd.write('\n')
    vault_ca = config.get('vault', {}).get('ca', None)
    if vault_ca is not None:
        full_name = 'vault' if suffix is None else 'vault' + suffix
        with open(path.join(cert_folder, full_name), 'w') as fd:
            fd.write(vault_ca)
            fd.write('\n')


def transform_json(json, filter_transform):
    '''Apply a filter on all the leaves of a json-like structure

    The function operates as side effect and transforms the structure.
    A single isolated leaf cannot be transformed.

    :param json: structure to transform (dictionnary/list tree of leaves)
    :filter_transform: function to apply on leaves.
    '''
    if isinstance(json, list):
        for (i, v) in enumerate(json):
            r = filter_transform(v)
            if r is not None:
                json[i] = r
            else:
                transform_json(v, filter_transform)
    elif isinstance(json, dict):
        for (k, v) in json.items():
            r = filter_transform(v)
            if r is not None:
                json[k] = r
            else:
                transform_json(v, filter_transform)
    else:
        pass


def b64(s):
    '''encode a utf-8 string in base64

    :param s: string to encode
    :return: encoded ascii string
    '''
    return base64.b64encode(s.encode('utf-8')).decode('ascii')


Json = Dict[str, Any]


class RunnableParams(NamedTuple):
    init: stages.Init
    conf: Json
    system: Json


class Runnable(NamedTuple):
    name: str
    priority: int
    code: Callable[[RunnableParams], None]


class BootParams(NamedTuple):
    conf: Json
    system: Json


class Bootable(NamedTuple):
    name: str
    priority: int
    code: Callable[[BootParams], None]


boot_runnables: List[Bootable] = []
std_runnables: List[Runnable] = []


class QuitCloudInit(Exception):
    '''Exception class used to abort cloud-init without error'''
    pass


def stop_cloud_init():
    '''Abort cloud-init'''
    raise QuitCloudInit


def run(arg: RunnableParams, min: Optional[int] = None):
    if min is None:
        runnables = std_runnables
    else:
        m = min
        runnables = list(filter(lambda r: r.priority >= m, std_runnables))
    try:
        for runnable in sorted(runnables, key=lambda e: e.priority):
            print(runnable.name)
            runnable.code(arg)
    except QuitCloudInit:
        pass


def runBoot(arg: BootParams):
    try:
        for runnable in sorted(boot_runnables, key=lambda e: e.priority):
            print(runnable.name)
            runnable.code(arg)
    except QuitCloudInit:
        pass


def register(
    name: str, priority: int,
    code: Callable[[RunnableParams], None],
):
    std_runnables.append(Runnable(name, priority, code))


def register_boot(
    name: str, priority: int, code: Callable[[BootParams], None]
):
    boot_runnables.append(Bootable(name, priority, code))

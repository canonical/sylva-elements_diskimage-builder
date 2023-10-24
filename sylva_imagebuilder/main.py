#  Copyright (C) 2021 Orange
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

import argparse
import importlib
import os
from os import path
import pkg_resources
import re
import subprocess

import jinja2
import jsonschema
import yaml

from typing import Any, Dict, List  # noqa: H301


def filter_regex_replace(value, pat, target):
    return re.sub(pat, target, value)


class ImageBuilder:
    '''Parameters of call to diskimage-builder'''

    def __init__(self):
        self.folders = []
        self.bools = []
        self.vars = {}
        self.options: List[Any] = []
        self.shell_env: List[Any] = []
        self.recipes: List[Any] = []
        self.packages: List[str] = []
        self.elements: List[str] = []
        self.osEnv: Dict[str, str] = {}
        self.env = jinja2.Environment()
        self.env.filters['regex_replace'] = filter_regex_replace
        schema_string = pkg_resources.resource_string(
            __name__, 'schema_config.yaml')
        schema = yaml.safe_load(schema_string)
        self.validator = jsonschema.Draft7Validator(schema)

    def setenv(self, var, value):
        os.environ[var] = value
        self.osEnv[var] = value

    def parse(self, modname):
        '''Parse a yaml config'''
        module = importlib.import_module(modname)
        folder = pkg_resources.resource_filename(module.__name__, '/')
        self.folders += [folder]
        with open(
            path.join(folder, 'config.yaml'),
            mode='r', encoding='utf-8'
        ) as fd:
            config = yaml.safe_load(fd)
            errors = 0
            for error in self.validator.iter_errors(config):
                errors += 1
                msg = error.message.replace('\n', '\n  ')
                err_path = '.'.join([str(e) for e in error.absolute_path])
                print(f'* {msg}')
                print(f'  at {"." if err_path == "" else err_path}')
            if errors > 0:
                raise Exception(
                    f'Invalid configuration ({errors} error(s)) in {folder}')
            self.options += config.get('options', [])
            self.shell_env += config.get('env', [])
            self.recipes += config.get('recipes', [])

    def valid(self, elt):
        when = elt.get('when', None)
        if when is not None:
            for cond in when:
                if cond[0] == '!':
                    ifValid = False
                    cond = cond[1:]
                else:
                    ifValid = True
                if '=' in cond:
                    [key, value] = cond.split('=', 1)
                    if (self.vars.get(key, None) != value) == ifValid:
                        return False
                else:
                    check = (cond not in self.bools and cond not in self.vars)
                    if check == ifValid:
                        return False
        return True

    def expand(self, value):
        "Jinja2 expansion of a template"
        return self.env.from_string(value).render(self.vars)

    def compute_git_url(self):
        """Compute the current git URL if possible.

        This is a hack but it provides a value to KANOD_GIT_URL that is
        often used in elements. This makes possible having reference
        relative to the current git server.
        """
        if 'DIB_KANOD_GIT_URL' in os.environ:
            return
        try:
            command = ['git', 'remote', 'get-url', 'origin']
            raw_url = subprocess.check_output(command, encoding='utf-8')
            git_url = path.dirname(raw_url.rstrip())
            self.setenv('DIB_KANOD_GIT_URL', git_url)
        except Exception:
            pass

    def compile(self, bools: List[str], vars: Dict[str, str]):
        for option in self.options:
            name = option.get('name', None)
            kind = option.get('kind', None)
            if name is None or kind is None:
                continue
            if kind == 'var':
                if name in vars:
                    val = vars[name]
                    choices = option.get('choices', None)
                    if choices is not None:
                        if val not in choices:
                            raise Exception(
                                f'{val} for {name} is not authorized')
                    self.vars[name] = val
                else:
                    default = option.get('default', None)
                    if default is not None:
                        self.vars[name] = default
            elif kind == 'flag':
                if name in bools:
                    self.bools += [name]
            else:
                raise Exception(f'Unknown kind {kind}')

        for env in self.shell_env:
            if not self.valid(env):
                continue
            name = env.get('name', None)
            value = env.get('value', None)
            if name is None or value is None:
                continue
            self.setenv(name, self.expand(value))

        for recipe in self.recipes:
            if not self.valid(recipe):
                continue

            def update(list, entry):
                new_content = recipe.get(entry, [])
                for raw_elt in new_content:
                    elt = self.expand(raw_elt)
                    if elt[0] == '!':
                        elt = elt[1:]
                        list[:] = [p for p in list if p != elt]
                    else:
                        list.append(elt)

            update(self.packages, 'packages')
            update(self.elements, 'elements')

    def run(self, name, additional, format):
        elements_path = [
            path.abspath(path.join(folder, 'elements'))
            for folder in self.folders]
        self.setenv('ELEMENTS_PATH', ':'.join(elements_path))
        self.setenv('PATH', (
            '/usr/local/bin:' + path.join(os.environ['HOME'], '.local/bin') +
            ':/usr/bin:/usr/sbin:/bin:/sbin'))
        packages = ','.join(self.packages)
        command = [
            'disk-image-create', '-a', 'amd64', '-t', format, '-o', name,
            '-p', packages, '-p', additional
        ] + self.elements
        if os.environ.get('KANOD_IMAGE_DEBUG', None) is not None:
            with open(os.environ['KANOD_IMAGE_DEBUG'], 'w') as fd:
                fd.write('#!/bin/bash\n\n')
                for (var, value) in self.osEnv.items():
                    fd.write(f'{var}={value}\n')
                fd.write(' '.join(command))
                fd.write('\n')
        subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('modules', nargs='*')
    parser.add_argument(
        '--output', '-o',
        help='name of the image'
    )
    parser.add_argument(
        '--bool', '-b', default=[], action='append',
        help='Define a boolean flag'
    )
    parser.add_argument(
        '--set', '-s', default=[], action='append', dest='decl',
        help='Define a variable with syntax key=value'
    )
    parser.add_argument(
        '--format', '-t', default='qcow2',
        help='Format of the image'
    )
    parser.add_argument(
        '--packages', '-p', default='',
        help='Additional packages (single comma separated list)'
    )
    args = parser.parse_args()
    image_builder = ImageBuilder()
    flags = args.bool
    vars = {}
    for decl in args.decl:
        if '=' in decl:
            [key, val] = decl.split('=', 1)
            vars[key.strip()] = val.strip()
        else:
            raise Exception(f'Incorrect binding syntax {decl}')

    modules = ['sylva_imagebuilder'] + args.modules

    for module in modules:
        image_builder.parse(module)

    image_builder.compute_git_url()
    image_builder.compile(flags, vars)
    output = args.output or 'img'
    if '.' not in output:
        output = f'{output}.{args.format}'
    image_builder.run(output, args.packages, args.format)

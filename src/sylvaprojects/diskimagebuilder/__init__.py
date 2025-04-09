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

import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
from os import path
from pathlib import Path
from typing import Any, Dict, List, Tuple  # noqa: H301

import importlib_resources
import jinja2
import jsonschema
import yaml


def filter_regex_replace(value, pat, target):
    return re.sub(pat, target, value)


def get_module_folder(modname: str) -> str:
    return str(importlib_resources.files(modname))


def get_module_file_content(modname: str, file_path: str) -> str:
    with importlib_resources.as_file(
        importlib_resources.files(modname) / file_path
    ) as path:
        return path.read_text()


class ImageBuilder:
    """Parameters of call to diskimage-builder"""

    def __init__(self):
        self.logger = logging.getLogger("ImageBuilder")
        self.folders: List[str] = []
        self.modules: List[str] = []
        self.bools: List[str] = []
        self.vars: Dict[str, Any] = {}
        self.options: List[Any] = []
        self.shell_env: List[Any] = []
        self.recipes: List[Any] = []
        self.packages: List[str] = []
        self.elements: List[str] = []
        self.osEnv: Dict[str, str] = {}
        self.env = jinja2.Environment()
        self.env.filters["regex_replace"] = filter_regex_replace
        schema_string = get_module_file_content(
            "sylvaprojects.diskimagebuilder", "schema_config.yaml"
        )
        schema = yaml.safe_load(schema_string)
        self.validator = jsonschema.Draft7Validator(schema)

    def setenv(self, var, value):
        self.logger.info(f"Setting env var {var} to {value}.")
        os.environ[var] = value
        self.osEnv[var] = value

    def add_module(self, modname):
        """Parse a module containing elements and a configuration"""
        self.logger.debug(f"Parsing module {modname}.")
        folder = get_module_folder(modname)
        if not folder:
            raise Exception(f"Could not find resources directory for module {modname}")
        self.modules.append(modname)
        self.logger.debug(f"Registering folder {folder} for module {modname}")
        self.folders.append(folder)

    def parse_config(self, config_file: str):
        """Parse a yaml config"""
        config_file = Path(config_file)
        config = yaml.safe_load(config_file.read_text())
        errors = 0
        error_msg = ""
        for error in self.validator.iter_errors(config):
            errors += 1
            msg = error.message.replace("\n", "\n  ")
            err_path = ".".join([str(e) for e in error.absolute_path])
            error_msg += f"* {msg}\n"
            error_msg += f'  at {"." if err_path == "" else err_path}\n'
        if errors > 0:
            self.logger.error(error_msg)
            raise Exception(
                f"Invalid configuration ({errors} error(s)) in {config_file}"
            )

        self.options += config.get("options", [])
        self.shell_env += config.get("env", [])
        self.recipes += config.get("recipes", [])

        for module in config.get("modules", []):
            self.add_module(module["name"])

    def valid(self, elt):
        when = elt.get("when", None)
        if when is not None:
            for cond in when:
                if cond[0] == "!":
                    ifValid = False
                    cond = cond[1:]
                else:
                    ifValid = True
                if "=" in cond:
                    [key, value] = cond.split("=", 1)
                    if (self.vars.get(key, None) != value) == ifValid:
                        return False
                else:
                    check = cond not in self.bools and cond not in self.vars
                    if check == ifValid:
                        return False
        return True

    def expand(self, value):
        "Jinja2 expansion of a template"
        return self.env.from_string(value).render(self.vars)

    def compile(self, bools: List[str], vars: Dict[str, str]):
        for option in self.options:
            name = option.get("name", None)
            kind = option.get("kind", None)
            if name is None or kind is None:
                continue
            if kind == "var":
                if name in vars:
                    val = vars[name]
                    choices = option.get("choices", None)
                    if choices is not None:
                        if val not in choices:
                            raise Exception(f"{val} for {name} is not authorized")
                    self.vars[name] = val
                else:
                    default = option.get("default", None)
                    if default is not None:
                        self.vars[name] = default
            elif kind == "flag":
                if name in bools:
                    self.bools += [name]
            else:
                raise Exception(f"Unknown kind {kind}")

        for env in self.shell_env:
            if not self.valid(env):
                continue
            name = env.get("name", None)
            value = env.get("value", None)
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
                    if elt[0] == "!":
                        elt = elt[1:]
                        list[:] = [p for p in list if p != elt]
                    else:
                        list.append(elt)

            update(self.packages, "packages")
            update(self.elements, "elements")

    def print_help(self):
        def print_option(v):
            name = v.get("name", "")
            descr = v.get("help", None)
            deflt = v.get("default", None)
            choices = v.get("choices", None)
            print(f"  {name}:")
            if descr is not None:
                indent = "    "
                for line in textwrap.wrap(
                    descr, initial_indent=indent, subsequent_indent=indent
                ):
                    print(line)
            if choices is not None:
                print(f'    allowed values: {", ".join(choices)}')
            if deflt is not None:
                print(f"    default value: {deflt}")

        options = sorted(self.options, key=lambda x: x.get("name", ""))
        print("\nvariables:")
        for v in options:
            if v.get("kind", None) == "var":
                print_option(v)
        print("\nflags:")
        for v in options:
            if v.get("kind", None) == "flag":
                print_option(v)

    def run(self, name, format, *, use_exec: bool = False):
        elements_path = [
            path.relpath(path.abspath(path.join(folder, "elements")), os.getcwd())
            for folder in self.folders
        ]

        self.setenv("ELEMENTS_PATH", ":".join(elements_path))
        self.setenv("PYTHONWARNINGS", "ignore::DeprecationWarning")

        if sys.version_info >= (3, 11):
            self.setenv(
                "PYTHONPATH",
                os.path.join(
                    get_module_folder("sylvaprojects.diskimagebuilder"), "hacks"
                ),
            )

        command = ["disk-image-create", "-a", "amd64", "-t", format, "-o", name]

        packages = ",".join(self.packages)
        if packages:
            command += ["-p", packages]

        command += self.elements

        self.logger.info(f"Running command {' '.join(map(shlex.quote, command))}")

        if os.environ.get("DIB_DEBUG", None) is not None:
            with open(os.environ["DIB_DEBUG"], "w") as fd:
                fd.write("#!/bin/bash\n\n")
                for var, value in self.osEnv.items():
                    fd.write(f"{var}={value}\n")
                fd.write(" ".join(command))
                fd.write("\n")
        if use_exec:
            os.execv(shutil.which(command[0]), command[2:])
        else:
            subprocess.run(command, check=True)

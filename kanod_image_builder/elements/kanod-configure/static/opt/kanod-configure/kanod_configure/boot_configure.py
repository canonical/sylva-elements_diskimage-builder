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

import importlib
from os import path
import pathlib
import sys

from cloudinit import util
from typing import Any, cast  # noqa: H301

from . import common


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


def initialize() -> None:
    print('initialize boot configure')
    if path.exists(common.SYSTEM_CONF):
        system = util.read_conf(common.SYSTEM_CONF)
    else:
        system = {}
    libraries = system.get('libraries') or []
    for library in libraries:
        mod = importlib.import_module(library)
        if hasattr(mod, 'init_boot'):
            cast(Any, mod).init_boot()
    return system


def main():
    '''Run boot kanod cloud-init boot command

    Run as configured in /etc/kanod-configure with live inputs given on stdin.
    '''
    # read_conf calls open. open can be given a file descriptor and will
    # wrap it. So we are just reading the config from stdin
    print('starting kanod-bootcmd')
    conf = util.read_conf(sys.stdin.fileno())
    system = initialize()
    try:
        common.run_boot(common.BootParams(conf, system))
        print('end of kanod bootcmd')
        pathlib.Path(common.MARK_FILE).touch()
        exit(0)
    except Exception as e:
        print('error during kanod bootcmd')
        print(e)
        exit(1)


if __name__ == '__main__':
    main()

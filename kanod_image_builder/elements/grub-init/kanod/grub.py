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

import subprocess
import sys

from kanod_configure import common


# TODO(pc): It is not clear that we want to keep it that way.
# A better abstraction would be a description of the huge pages we want
# for example.
def configure_grub(arg: common.BootParams):
    '''Configure grub command line at first boot'''
    print('grub configure')
    grub_line = arg.conf.get('grub', None)
    if grub_line:
        command = ['/usr/local/bin/grub-init', grub_line]
        proc = subprocess.run(
            command, stdout=sys.stdout, stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            print('grubinit failed')


common.register_boot('Grub configuration', 50, configure_grub)

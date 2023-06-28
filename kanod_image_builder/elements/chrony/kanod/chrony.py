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

from cloudinit.distros import rhel, opensuse
from cloudinit import subp

from kanod_configure import common


def ntp_config(arg: common.RunnableParams):
    distro = arg.init.distro
    '''Configure ntp client service'''
    ntp_vars = arg.conf.get('ntp')
    chrony_daemon = 'chrony'
    if isinstance(distro, rhel.Distro) or isinstance(distro, opensuse.Distro):
        chrony_daemon = 'chronyd'
    if ntp_vars is not None:
        print(f'Configure chrony with daemon {chrony_daemon}')
        common.render_template(
            'chrony.tmpl', 'etc/chrony/chrony.conf', ntp_vars)
        subp.subp(['systemctl', 'enable', chrony_daemon])
        subp.subp(['systemctl', 'restart', chrony_daemon])


common.register('NTP configuration', 100, ntp_config)

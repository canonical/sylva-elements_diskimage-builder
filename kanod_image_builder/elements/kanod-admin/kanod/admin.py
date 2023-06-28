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


def configure_admin(arg: common.RunnableParams):
    '''Configuration of a base admin user'''
    distro = arg.init.distro
    admin = arg.conf.get('admin', None)
    if admin is not None:
        passwd = admin.get('passwd', None)
        args = {
            'sudo': ['ALL=(ALL) NOPASSWD:ALL'],
            'ssh_authorized_keys': admin.get('keys', []),
            'groups': 'wheel',
            'shell': '/bin/bash',
        }
        if passwd is not None:
            args['plain_text_passwd'] = passwd
            args['lock_passwd'] = False
        distro.create_user(admin.get('username', 'admin'), **args)


common.register('Admin user configuration', 110, configure_admin)

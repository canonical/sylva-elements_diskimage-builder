#  Copyright (C) 2022 Orange
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


def greeter(arg: common.RunnableParams):
    '''Register a new greeting'''
    greeter = arg.conf.get('greeting', None)
    if greeter is None:
        print('* no greeter configured')
        return
    with open('/etc/issue', 'w', encoding='utf-8') as fd:
        fd.write(greeter)
        fd.write(' - \\n \\l\n')
    with open('/etc/issue.net', 'w', encoding='utf-8') as fd:
        fd.write(greeter)


common.register('Greeter', 100, greeter)

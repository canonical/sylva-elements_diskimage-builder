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

from os import path
import re
import subprocess
import sys

from kanod_configure import common

KANOD_VG = 'vg'


def get_underlying_pv(vg):
    '''Gets the partition supporting a volume group

    :param vg: the name of the volume group
    :returns: a list of physical partition supporting the volume group.
    '''
    command = ['pvs', '--noheading', '-o', 'pv_name,vg_name']
    output = subprocess.check_output(command, encoding='utf-8')
    lines = re.split('\n', output.strip())
    entries = [re.split('[ \n\t]+', line.strip()) for line in lines]
    return [pvname for [pvname, vgname] in entries if vgname == vg]


def fill_lvm_disk(conf):
    '''Extend lvm partitions filling the disk'''
    pvs = get_underlying_pv(KANOD_VG)
    if len(pvs) == 0:
        print('* did not find underlying physical volume.')
        return
    root_fs = pvs[0]
    match = re.search('(.*[^0-9])([0-9]*)$', root_fs)
    root_disk = re.sub ('([0-9]+)p$', r"\1", match.group(1))
    fs_num = match.group(2)
    proc = subprocess.run(
        ['growpart', root_disk, fs_num],
        stdout=sys.stdout, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        print('* cannot grow partition')
    else:
        proc = subprocess.run(
            ['pvresize', '-y', '-q', root_fs],
            stdout=sys.stdout, stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            print('* cannot grow kanod volume group')


def grow_lvm_volumes(lvm_parts):
    for spec in lvm_parts:
        name = spec.get('name', None)
        size = spec.get('size', None)
        if name is None or size is None:
            continue
        opt = '-l' if '%' in size else '-L'
        proc = subprocess.run(
            ['lvresize', '-y', '-q', '-r', opt, size,
             f'/dev/mapper/vg-{name}'],
            stdout=sys.stdout, stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            print(f'* Cannot grow volume vg-{name}')


def configure_lvm(args: common.BootParams):
    print('lvm configure')
    if not path.exists(f'/dev/{KANOD_VG}'):
        print('* Kanod LVM volume group not found')
        return
    if path.exists(common.MARK_FILE):
        print('* run only on first boot.')
        return
    lvm_parts = args.conf.get('lvm', None)
    if lvm_parts is None:
        # Doing a default partitioning is more sensible than doing nothing.
        # We cannot expect every cloud operator to define a partitioning of
        # base image.
        print(' *Using default partitioning')
        # Default partitioning gives 2/3 to var because containers are the
        # main reason for expansion on standard nodes.
        lvm_parts = [
            {'name': 'lv_varlog', 'size': '+10%FREE'},
            {'name': 'lv_tmp', 'size': '+10%FREE'},
            {'name': 'lv_root', 'size': '+20%FREE'},
            {'name': 'lv_home', 'size': '+10%FREE'},
            {'name': 'lv_vartmp', 'size': '+10%FREE'},
            {'name': 'lv_varlogaudit', 'size': '+5%FREE'},
            {'name': 'lv_var', 'size': '100%FREE'},
        ]
    fill_lvm_disk(args.conf)
    grow_lvm_volumes(lvm_parts)


common.register('Configure LVM', 7, configure_lvm)

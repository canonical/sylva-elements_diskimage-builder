
`Diskimage-builder` is a tool for automatically building customized operating-system images for use in clouds and other environments. Diskimage-builder is used extensively by the TripleO project and within OpenStack Infrastructure.



**Supported Image Formats:** 
qcow2(default), tar, tgz, squashfs, vhd, docker, raw



**Tested OS:** 
* centos-minimal: CentOS 7, 8-stream and 9-stream
* fedora-containerfile: the latest Fedora
* ubuntu-minimal: Ubuntu Xenial, Bionic and Focal
* debian-minimal: Bullseye



## How to use it


**Requirements**

Most image formats require `qemu-utils` package installed on Ubuntu/Debian.

If you want to generate images with partitions, the `kpartx` tool needs to be installed.





**Installation**



For development purposes, you can use `pip -e` to install the latest git tree checkout into a local testing virtualenv.
The recommended way is to use provided `tox` environments:


```shell
git clone https://opendev.org/openstack/diskimage-builder

cd diskimage-builder

tox -e bindep

sudo apt-get install <any-missing-packages-from-bindep>

tox -e venv -- disk-image-create ...
```




**Building an image**



* To create a bootable image using a supported distribution(element) and _qcow2_ format use the following command: 

```shell
disk-image-create <options> <element>
```
- Other output formats may be specified using the _-t <format>_ option.
- Output image name may be specified using _-o <name>_ option.
- Specify default installation type with *--install-type --* option.


* To create a bootable vm image using _ubuntu_ element and _raw_ format use the following command: 

```shell
disk-image-create ubuntu vm -t raw
```





**Key concepts**



* **Install types** permit elements to be installed from different sources, such as git repositories, distribution packages or pip. 
The default is source, and it can be modified in the disk-image-create command line via the *–install-type* option or you can set *DIB_DEFAULT_INSTALLTYPE* variable.



* **Elements** are how we decide what goes into our image and what modifications will be performed.
All elements can be found under *diskimage_builder/elements*, and you can create new elements following the conventions for environment variables. (https://docs.openstack.org/diskimage-builder/latest/developer/developing_elements.html)


* **Elements** directory structure:


```shell
ubuntu@sylva:~/diskimage-builder/diskimage_builder/elements$ ls
__init__.py                  cloud-init-nocloud   dracut-network         install-bin           pip-and-virtualenv         source-repositories
__pycache__                  containerfile        dracut-ramdisk         install-static        pip-cache                  stable-interface-names
apt-conf                     debian               dracut-regenerate      install-types         pkg-map                    svc-map
apt-preferences              debian-minimal       dynamic-login          iscsi-boot            posix                      sysctl
apt-sources                  debian-systemd       element-manifest       iso                   proliant-tools             sysprep
baremetal                    debian-upstart       elrepo                 journal-to-console    pypi                       tpm-emulator
base                         debootstrap          enable-serial-console  keylime-agent         python-brickclient         uboot
block-device-efi             deploy-baremetal     ensure-venv            local-config          python-stow-versions       ubuntu
block-device-efi-lvm         deploy-kexec         epel                   lvm                   ramdisk                    ubuntu-common
block-device-gpt             deploy-targetcli     fedora                 manifests             ramdisk-base               ubuntu-minimal
block-device-mbr             deploy-tgtadm        fedora-container       mellanox              rax-nova-agent             ubuntu-signed
bootloader                   devuser              fedora-minimal         modprobe              redhat-common              ubuntu-systemd-container
cache-url                    dhcp-all-interfaces  gentoo                 modprobe-blacklist    rhel                       vm
centos                       dib-init-system      growroot               no-final-image        rhel-common                yum
centos-minimal               dib-python           growvols               oat-client            rhel7                      yum-minimal
centos7                      dib-run-parts        grub2                  openeuler-minimal     rocky-container            zipl
cleanup-kernel-initrd        disable-nouveau      hpdsa                  openssh-server        rpm-distro                 zypper
cloud-init                   disable-selinux      hwburnin               openstack-ci-mirrors  runtime-ssh-host-keys      zypper-minimal
cloud-init-datasources       dkms                 hwdiscovery            opensuse              select-boot-kernel-initrd
cloud-init-disable-resizefs  docker               ibft-interfaces        opensuse-minimal      selinux-permissive
cloud-init-growpart          dpkg                 ilo                    package-installs      simple-init
```





## Disk Image Layout



The number of images, partitions, disk encryption and other features should be set up during the initial image build, since it’s not possible to change them later on.



**Limitations**



There are currently three fixed keys used, which are not configurable:

*   _root-label_: this is the label of the block device that is mounted at /.

*   _image-block-partition_: if there is a block device with the name root it is used, else the block device with the name image0 is used.

*   _image-path_: the path of the image that contains the root file system is taken from the image0.




There are currently two defaults:

*	When using the **vm** element, an element that provides block-device should be included. 
Available _block-device-*_ elements cover the common case of a single partition that fills up the whole disk and used as root device. Currently there are MBR, GPT and EFI versions. For example, to use a GPT disk you could build with:

```shell
disk-image-create -o output.qcow vm block-device-gpt ubuntu-minimal
```

*	When the **vm** element is not used, a plain filesystem image without any partitioning is created.



If you wish to customise the top-level block-device-default.yaml file from one of the _block-device-* elements_, set the environment variable *DIB_BLOCK_DEVICE_CONFIG*. This variable must hold YAML structured configuration data or be a file:// URL reference to a on-disk configuration file.






## Block Device Modules



Modules can be found under *diskimage_builder/block_device*. They provide options for different levels, with configuration specified as a tree or digraph:

* Level 0 **Local Loop**: generates a local image file and uses the loop device to create a block device from it.

Example:
```shell
local_loop:
  name: image0

local_loop:
  name: data_image
  size: 7.5GiB
  directory: /var/tmp
```


* Level 1 **Partitioning**: generates partitions on existing block devices. This means that it is possible to take any kind of block device (e.g. LVM, encrypted, …) and create partition information in it. Partitions are created in the order they are configured.

Example:
```shell
- partitioning:
    base: image0
    label: mbr
    partitions:
      - name: part-01
        flags: [ boot ]
        size: 1GiB
      - name: part-02
        size: 100%
```


* Level 1 **LVM**:  generates volumes on existing block devices. This means that it is possible to take any previous created partition, and create volumes information in it.

Example:
```shell
- lvm:
    name: lvm
    pvs:
      - name: pv
        options: ["--force"]
        base: root

    vgs:
      - name: vg
        base: ["pv"]
        options: ["--force"]

    lvs:
      - name: lv_root
        base: vg
        size: 1800M

      - name: lv_tmp
        base: vg
        size: 100M

      - name: lv_var
        base: vg
        size: 500M

      - name: lv_log
        base: vg
        size: 100M

      - name: lv_audit
        base: vg
        size: 100M

      - name: lv_home
        base: vg
        size: 200M
```



* Level 2 **Mkfs**: creates file systems on the block device given as base.

Example
```shell
- mkfs:
    name: mkfs_root
    base: root
    type: ext4
    label: cloudimage-root
    uuid: b733f302-0336-49c0-85f2-38ca109e8bdb
    opts: "-i 16384"
```



* Level 3 **Mount**: mounts a filesystem.

Example
```shell
- mount:
    name: root_mnt
    base: mkfs_root
    mount_point: /
```



* Level 4 **Fstab**: creates fstab entries. 

Example
```shell
- fstab:
    name: var_log_fstab
    base: var_log_mnt
    options: nodev,nosuid
    dump-freq: 2
```





## OS Hardening



Depending on which elements you decide to use for building an image, you should take into consideration what **pre-install** and **post-install** scripts need to be applied.



Example of _ubuntu_ basic element structure:


```shell
README.rst  element-deps  element-provides  environment.d  package-installs.yaml  post-install.d  pre-install.d  root.d  test-elements
```

* in _element-deps_            specify dependencies on other elements

* in _element-provides_        list of elements provided by current element

* in _environment.d_           define environment variables and data sources

* in _package-installs_        specify packages to be installed

* in _post-install.d_          define post-install scripts to be called after install, but before first image boot

* in _pre-install.d_           define pre-install scripts, good place to add apt repositories

* in _root.d_                  adapt the initial root filesystem

* in _test-elements_           various build-succeed tests


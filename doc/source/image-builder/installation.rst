Script installation
===================

You need ``disk-image-create`` in your path. It is supplied by the
Openstack ``diskimage-builder`` project. You must use a recent version
(>= 3.2.1)  to create images that are both EFI and
BIOS bootable. Use ``pip3 install diskimage-builder``.

The tool requires various packages to run mainly related to package management
both for Ubuntu and CentOS. The following packages are necessary on an Ubuntu
system:

* ``qemu-utils``
* ``debootstrap``
* ``gdisk``
* ``kpartx``
* ``dosfstools``
* ``rpm``
* ``yum-utils``

on a CentOS system, you must install:

* ``qemu-img``
* ``debootstrap``
* ``gdisk``
* ``yum-utils``
* ``policycoreutils-python-utils``

and *disable* SELinux.

The main command is installed with ``python3 -m pip install --user .``.


# Kanod Image Builder

Kanod-image-builder ( an extension of diskimage-builder)  is a tool used in the OpenStack ecosystem for building customized operating system images suitable for use in cloud environments. 

When images have been analyzed and are considered safe enough, a tag is set on a protected branch (with $COSIGN_PRIVATE_KEY variable available) so that the project can sign the images. The signatures are stored in the same OCI registry as the images.


## Kanod Intro
Using kanod-image-builder involves defining your image requirements in a set of configuration files, specifying the elements (modules) to include, and then running the kanod-image-builder command to build the image. 

Kanod_image_builder directory structure:
```
$ ~/diskimage-builder/kanod_image_builder$ tree
.
├── __init__.py
├── config.yaml
├── elements
│   ├── block-device-kanod-lvm
│   ├── build-info
│   ├── chrony
│   ├── cis-remediation
│   ├── cloud-init-growpart
│   ├── containers
│   ├── fix-secureboot
│   ├── grub-config
│   ├── grub-init
│   ├── kanod-admin
│   ├── kanod-cloud-init
│   ├── kanod-configure
│   ├── kanod-docker
│   ├── kanod-mirror
│   ├── klvm
│   ├── kubeadm
│   │   └── post-install.d
│   │       └── 99-kubeadm
│   ├── nexus
│   ├── nginx
│   ├── python38
│   ├── rename-interface-names
│   ├── rke2-airgapped
│   ├── tpm2tools
│   └── ubuntu-fix
├── main.py
├── my_custom_image.d
└── schema_config.yaml
```

A DIB (Disk Image Builder) element is a set of scripts and configuration files that define how to build a particular part of the image (e.g., base operating system, packages, configurations).

<strong>config.yaml</strong> file describes a list of elements used for image customization.
<details>
  <summary>config.yaml</summary>

```
recipes:
- elements:
  - kanod-mirror
  - kanod-cloud-init
  - kanod-admin
  - vm
  - openssh-server
  - runtime-ssh-host-keys
  - growroot
  - bootloader
  - grub-init
  - kanod-configure
  - chrony
  - build-info
# Recipe for Ubuntu images
- when:
  - target=ubuntu
  # Packages to install
  packages:
  - initramfs-tools
  - parted
  - kbd
  - lvm2
  - netplan.io
  - cryptsetup
  - less
  elements:
  - ubuntu{{ "" if image is defined else "-minimal" }}
  - ubuntu-fix
  - klvm
  - fix-secureboot
  ```
</details>

<strong>Elements</strong> directory contains necessary scripts and configurations for image customization. Such example module is kubeadm customization module:

<strong>99-kubeadm</strong> is an example script for kubeadm install.
<details>
  <summary>99-kubeadm</summary>

```
#!/bin/bash

set -eu

tee /etc/modules-load.d/kubernetes.conf <<EOF
overlay
br_netfilter
EOF
tee /etc/sysctl.d/kubernetes.conf <<EOF
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
EOF

curl -sL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/kubernetes-keyring.gpg
apt-add-repository -y "deb http://apt.kubernetes.io/ kubernetes-xenial main"
apt -y install containerd
mkdir /etc/containerd
containerd config default | sed 's/SystemdCgroup = false/SystemdCgroup = true/' | tee /etc/containerd/config.toml
export K8S_VERSION=${K8S_VERSION%-*}
apt install -y kubelet=$K8S_VERSION-00 kubeadm=$K8S_VERSION-00 kubectl=$K8S_VERSION-00
```
</details>

## Install diskimage-builder

The tool requires various packages to run mainly related to package management both for Ubuntu and CentOS. The following packages are necessary on an Ubuntu system:
- qemu-utils
- debootstrap
- gdisk
- kpartx
- dosfstools
- rpm
- yum-utils

on a CentOS system, you must install:
- qemu-img
- debootstrap
- gdisk
- yum-utils
- policycoreutils-python-utils

and disable SELinux.

```
pip3 install diskimage-builder
```
## CI/CD image build 

Images created during build stage will be saved at: https://gitlab.com/sylva-projects/sylva-elements/diskimage-builder/container_registry


## Manual Usage

In ~/diskimage-builder$ directory run:
```
python3 -m pip install --user . --break-system-packages
export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"
```

Run the kanod-image-builder command, specifying the desired image format, target distribution, and the output image file.
```
kanod-image-builder [-s ‘key=value’]* [-b flag]* <additional module>

    -b flag (--bool flag) set the flag flag to true
    -s key=val (--set key=val) set the option key to value val
    -o output defines the name of the image to be output.qcow2. The build will also generate an output-schema.yaml
    --packages p1,p2...,pn adds the comma separated list of packages to the build.
```
Example for local manual image build with kanod-image-builder:
```
# simple example without flags
kanod-image-builder -s target=ubuntu -s release=jammy --format qcow2 -o my_custom_image.qcow2
# or with flags
kanod-image-builder -s target=ubuntu -s release=jammy -b no_kanod_network -b rke2_airgapped --format qcow2 -o my_custom_image.qcow2
```

## Documentation:

* building and designing images: https://orange-opensource.gitlab.io/kanod/reference/image-builder/index.html
* core library: https://orange-opensource.gitlab.io/kanod/reference/machines/core/index.html
* signature: https://docs.sigstore.dev/cosign/overview/

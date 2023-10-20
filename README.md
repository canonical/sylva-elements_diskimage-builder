# Kanod Image Builder

CLI and core library to build custom OS image in Kanod.

Documentation: 

* building and designing images: https://orange-opensource.gitlab.io/kanod/reference/image-builder/index.html
* core library: https://orange-opensource.gitlab.io/kanod/reference/machines/core/index.html


# Available artifacts:

* 0.0.11 (latest)
  * bump k8s version to v1.26.9

```bash
k8s 1.26.9
oci://registry.gitlab.com/sylva-projects/sylva-elements/diskimage-builder/ubuntu-jammy-plain-kubeadm-1.26.9:0.0.12
sha256: 2f63618e0a97b9316e64bc4fc8947524978397b07bc5d23db7ddf325e7d11b9e

oci://registry.gitlab.com/sylva-projects/sylva-elements/diskimage-builder/ubuntu-jammy-hardened-rke2-1.26.9:0.0.12
sha256: 2b2204746d0ded5515247bf0a410a4956d5202ca42e91a04228d071c07388337

oci://registry.gitlab.com/sylva-projects/sylva-elements/diskimage-builder/ubuntu-jammy-plain-rke2-1.26.9:0.0.12
sha256: ffdc81fcdc0104151aa792a508eefe0d47660b18683949edcd734b3a4f938f20



k8s 1.24.17
oci://registry.gitlab.com/sylva-projects/sylva-elements/diskimage-builder/ubuntu-jammy-plain-kubeadm-1.26.9:0.0.12
sha256: 2f63618e0a97b9316e64bc4fc8947524978397b07bc5d23db7ddf325e7d11b9e

oci://registry.gitlab.com/sylva-projects/sylva-elements/diskimage-builder/ubuntu-jammy-hardened-rke2-1.26.9:0.0.12
sha256: 2b2204746d0ded5515247bf0a410a4956d5202ca42e91a04228d071c07388337

oci://registry.gitlab.com/sylva-projects/sylva-elements/diskimage-builder/ubuntu-jammy-plain-rke2-1.24.17:0.0.12
sha256: 21471d8064e4518dce8aee643fddcd82386a712d69d8ff863759ef0df9225df0
```

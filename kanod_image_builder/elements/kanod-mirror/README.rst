kanod-mirror
============

This element defines settings to simplify the use of various mirrors during
image build:

* deb and rpm mirror
* pypi mirrors
* others...

One of the challenge is to have a set of variables that are specific to each
distribution.

* DIB_UBUNTU_MIRROR and DIB_CENTOS_MIRROR define DIB_DISTRIBUTION_MIRROR for
  respectively ubuntu and centos.
* DIB_PYPI_MIRROR_URL can be defined for using a python pip mirror.

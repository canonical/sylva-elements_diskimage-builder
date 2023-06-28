Core Image
==========
The fields of the core image should be present in most OS images. They
represent the core services that can be configured in a base OS (networking,
ntp)

Configuration Variables
-----------------------

``target``
    Targetted OS family. Supported names are ubuntu, centos and opensuse.

``release``
    Version of the OS (family dependent)

``image_size``
   Size of the generated disk

``packages``
   Additional packages to preload (comma separated list)

``secret``
    Adding this setting will trigger the definition of a user with login devuser
    and as password the value of this setting. Additional packages may be
    installed to simplify debugging. As the name implies, only use this setting
    for debugging. Typically connection should be possible with this user from
    the console.

``image``
    The setting if defined triggers a full build from a standard image rather
    than a minimal build. If the value is ``-`` the build will be done with
    the default image for the OS release, otherwise the file provided will be 
    used instead (a squashfs filesystem for Ubuntu, a qcow2 for centos).
    Alternative image is not supported by OpenSuse.

Configuration Flags
-------------------

``tpm``
    enables TPM support
``lvm``
    LVM partitionning of the base image
``cis_remediation``
    Applies some basic CIS remediation (limited to Ubuntu)
``rename_interface_names``
    If set, prevent the application of predictive interface naming
``no_kanod_network``
    Let standard cloud-init handle the network. Do not disable network manager.



.. jsonschema:: schema.yaml
    :lift_title:
    :lift_description:
    :lift_definitions:
    :auto_reference:
    :auto_target:
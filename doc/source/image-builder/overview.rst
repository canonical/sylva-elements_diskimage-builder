Usage
=====

This is the core tool for building OS images using kanod-configure in cloud-init
for specialization. Images are built using information in specific folders given
on the command line.

A typical call is:

    kanod-image-builder [-s 'key=value']* [-b flag]* <additional module>

* ``-b flag`` (``--bool flag``) set the flag ``flag`` to true
* ``-s key=val`` (``--set key=val``) set the option ``key`` to value ``val``
* ``-o output`` defines the name of the image to be ``output.qcow2``. The build
  will also generate an ``output-schema.yaml``
* ``--packages p1,p2...,pn`` adds the comma separated list of packages to the
  build.


``kanod-node``, ``common-services``, ``gogs-service`` are examples of projects
providing specialized images for Kanod.

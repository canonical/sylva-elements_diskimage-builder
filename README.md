# Kanod Image Builder

CLI and core library to build custom OS image in Kanod.

When images have been analyzed and are considered safe enough, a tag is set on a protected branch (with $COSIGN_PRIVATE_KEY variable available) so that the project can sign the images. The signatures are stored in the same OCI registry as the images.

Documentation:

* building and designing images: https://orange-opensource.gitlab.io/kanod/reference/image-builder/index.html
* core library: https://orange-opensource.gitlab.io/kanod/reference/machines/core/index.html
* signature: https://docs.sigstore.dev/cosign/overview/

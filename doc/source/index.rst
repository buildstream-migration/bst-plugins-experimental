.. toctree::
   :maxdepth: 2

BuildStream-External Documentation
==================================

This is a collection of plugins that are either tailored to a very specific use
case, or need to change faster than would be allowed by the long term stable
API guarantees that we expect of core BuildStream plugins.

To use one of these plugins in your project you need to have installed the
bst-external package and enabled it in your `project configuration file
<https://buildstream.gitlab.io/buildstream/projectconf.html#plugin-origins-and-versions>`_.

.. toctree::
   :maxdepth: 1
   :caption: Contained Elements

   elements/dpkg_build
   elements/dpkg_deploy
   elements/x86image
   elements/flatpak_image
   elements/flatpak_repo
   elements/collect_integration
   elements/collect_manifest
   elements/fastboot_bootimg
   elements/fastboot_ext4
   elements/tar_element
   elements/oci

.. toctree::
   :maxdepth: 1
   :caption: Contained Sources

   sources/docker
   sources/quilt
   sources/git_tag

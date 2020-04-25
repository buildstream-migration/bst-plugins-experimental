.. toctree::
   :maxdepth: 2

bst-plugins-experimental Documentation
======================================

This is a collection of plugins to use with Buildstream

To use one of these plugins in your project you need to have installed the
bst-plugins-experimental package and enabled it in your `project configuration file
<https://buildstream.gitlab.io/buildstream/projectconf.html#plugin-origins-and-versions>`_.

.. toctree::
   :maxdepth: 1
   :caption: Contained Elements

   elements/bazel_build
   elements/cmake
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
   elements/meson
   elements/make
   elements/makemaker
   elements/modulebuild
   elements/qmake
   elements/distutils
   elements/oci
   elements/pip

.. toctree::
   :maxdepth: 1
   :caption: Contained Sources

   sources/bazel_source
   sources/bzr
   sources/cargo
   sources/deb
   sources/ostree
   sources/pip
   sources/quilt
   sources/git_tag
   sources/tar

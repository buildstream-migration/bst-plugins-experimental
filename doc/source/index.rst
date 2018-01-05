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

Contained Elements
------------------

* :mod:`dpkg_build <elements.dpkg_build>`
* :mod:`dpkg_deploy <elements.dpkg_deploy>`
* :mod:`x86image <elements.x86image>`

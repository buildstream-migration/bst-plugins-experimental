BuildStream Plugins
*******************

A collection of plugins for the BuildStream project.

How to use this repo
====================

At the moment, this repo is a sort of incubation repo; it contains things
which explicitly don't yet have strong API guarantees.

Therefore, for the time being we recommend use bst-plugins-experimental as a submodule
for your buildstream projects.

Using the plugins locally within a project
------------------------------------------
To use the bst-plugins-experimental plugins locally within a
`BuildStream <https://gitlab.com/BuildStream/buildstream>`_
project, you will first need to clone the repo to a location **within your
project**::

    git clone https://gitlab.com/BuildStream/bst-plugins-experimental.git

The plugins must be declared in *project.conf*. To do this, please refer
to BuildStream's
`Local plugins documentation <https://buildstream.gitlab.io/buildstream/format_project.html#local-plugins>`_.

Using the plugins as a Python package
-------------------------------------
To use the bst-plugins-experimental plugins as a Python package within a
`BuildStream <https://gitlab.com/BuildStream/buildstream>`_
project, you will first need to install bst-plugins-experimental via pip::

    git clone https://gitlab.com/BuildStream/bst-plugins-experimental.git
    cd bst-plugins-experimental
    pip install --user -e .

To ensure it's installed, try: ``pip show bst-plugins-experimental``, this should
show information about the package.

.. note::
   The -e option ensures that changes made to the git repository are reflected
   in the Python package's behaviour.

Then, the plugins must be declared in the *project.conf*. The implementation of
this is explained in BuildStream's
`Pip plugins documentation <https://buildstream.gitlab.io/buildstream/format_project.html#pip-plugins>`_

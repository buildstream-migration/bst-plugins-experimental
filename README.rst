BuildStream Plugins
*******************

A collection of plugins for the BuildStream project that are too
specific or prone to change for inclusion in the main repository.

How to use this repo
====================

At the moment, this repo is a sort of incubation repo; it contains things
which explicitly don't yet have strong API guarantees.

Therefore, for the time being we recommend use bst-external as a submodule
for your buildstream projects.

Using the plugins locally within a project
------------------------------------------
To use the bst-external plugins locally within a
`BuildStream <https://gitlab.com/BuildStream/buildstream>`_
project, you will first need to clone the repo to a location **within your
project**::

    git clone https://gitlab.com/BuildStream/bst-external.git

The plugins must be declared in *project.conf*. To do this, please refer
to BuildStream's
`Local plugins documentation <https://buildstream.gitlab.io/buildstream/format_project.html#local-plugins>`_.

Using the plugins as a Python package
-------------------------------------
To use the bst-external plugins as a Python package within a
`BuildStream <https://gitlab.com/BuildStream/buildstream>`_
project, you will first need to install bst-external via pip::

    git clone https://gitlab.com/BuildStream/bst-external.git
    cd bst-external
    pip install --user -e .

To ensure it's installed, try: ``pip show BuildStream-external``, this should
show information about the package.

.. note::
   The -e option ensures that changes made to the git repository are reflected
   in the Python package's behaviour.

Then, the plugins must be declared in the *project.conf*. The implementation of
this is explained in BuildStream's
`Pip plugins documentation <https://buildstream.gitlab.io/buildstream/format_project.html#pip-plugins>`_

Pre-review checklist
====================

Before submitting for review, please check the following:

1. Any new plugins have:
   1.1 Added have a copyright statement attached.
   1.2 An entry point defined in setup.py.
   1.3 Been added to the list in ``doc/source/index.rst``

2. It can be tested. Ideally, with automated tests. At minimum, instructions
   on how the maintainer can test it for themselves.

3. Any non-trivial change that is visible to the user should have a note
   in NEWS describing the change.

   Typical changes that do not require NEWS entries:

   * Typo fixes
   * Formatting changes
   * Internal Refactoring

   Typical changes that do require NEWS entries:

   * Bug fixes
   * New features

Release Policy
==============

The maintainer will create a new release in response to changes that are
significant to users.
The steps to do this are:

1. Check for changes between releases that do not have a NEWS entry.
   1.1. Add any new plugins to the list in ``doc/source/index.rst``.
   1.2. Check that new plugins have an entrypoint in setup.py
2. Create a new release number in NEWS.
3. Update the version in setup.py
4. Update the variables ``version`` and ``release`` in ``doc/source/conf.py``
5. Create and push an annotated tag for this version, containing all the
   items from the latest NEWS entry.


Significant changes include:

* Important bugfixes
* Non-backward-compatible changes
* Specifically-requested changes.

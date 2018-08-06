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

Pre-review checklist
====================

Before submitting for review, please check the following:

1. It can be tested. Ideally, with automated tests. At minimum, instructions
   on how the maintainer can test it for themselves.

2. Any non-trivial change that is visible to the user should have a note
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
1. Check for changese between releases that do not have a NEWS entry.
2. Create a new release number in NEWS.
3. Update the version in setup.py
4. Create and push an annotated tag for this version, containing all the
   items from the latest NEWS entry.


Significant changes include:
* important bugfixes
* non-backward-compatible changes
* specifically-requested changes.

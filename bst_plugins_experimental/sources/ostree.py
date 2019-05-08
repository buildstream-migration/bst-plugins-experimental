#
#  Copyright (C) 2018 Codethink Limited
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Andrew Leeming <andrew.leeming@codethink.co.uk>
#        Tiago Gomes <tiago.gomes@codethink.co.uk>

"""
ostree - stage files from an OSTree repository
==============================================

**Usage:**

.. code:: yaml

   # Specify the ostree source kind
   kind: ostree

   # Specify the repository url, using an alias defined
   # in your project configuration is recommended.
   url: upstream:runtime

   # Optionally specify a symbolic tracking branch or tag, this
   # will be used to update the 'ref' when refreshing the pipeline.
   track: runtime/x86_64/stable

   # Specify the commit checksum, this must be specified in order
   # to checkout sources and build, but can be automatically
   # updated if the 'track' attribute was specified.
   ref: d63cbb6fdc0bbdadc4a1b92284826a6d63a7ebcd

   # For signed ostree repositories, specify a local project relative
   # path to the public verifying GPG key for this remote.
   gpg-key: keys/runtime.gpg

See :ref:`built-in functionality doumentation <core_source_builtins>` for
details on common configuration options for sources.
"""

import os
import shutil

from gi.repository import GLib, Gio, OSTree  # noqa
from buildstream import Source, SourceError, Consistency
from buildstream import utils
from ._ostree import OSTreeError
from . import _ostree


class OSTreeSource(Source):

    def configure(self, node):

        self.node_validate(node, ['url', 'ref', 'track', 'gpg-key', *Source.COMMON_CONFIG_KEYS])

        self.original_url = self.node_get_member(node, str, 'url')
        self.url = self.translate_url(self.original_url)
        self.ref = self.node_get_member(node, str, 'ref', None)
        self.tracking = self.node_get_member(node, str, 'track', None)
        self.mirror = os.path.join(self.get_mirror_directory(),
                                   utils.url_directory_name(self.original_url))

        # At this point we now know if the source has a ref and/or a track.
        # If it is missing both then we will be unable to track or build.
        if self.ref is None and self.tracking is None:
            raise SourceError("{}: OSTree sources require a ref and/or track".format(self),
                              reason="missing-track-and-ref")

        # (optional) Not all repos are signed. But if they are, get the gpg key
        self.gpg_key_path = None
        if self.node_get_member(node, str, 'gpg-key', None):
            self.gpg_key = self.node_get_project_path(node, 'gpg-key',
                                                      check_is_file=True)
            self.gpg_key_path = os.path.join(self.get_project_directory(), self.gpg_key)

        # Our OSTree repo handle
        self.repo = None

    def preflight(self):
        pass

    def get_unique_key(self):
        return [self.original_url, self.ref]

    def load_ref(self, node):
        self.ref = self.node_get_member(node, str, 'ref', None)

    def get_ref(self):
        return self.ref

    def set_ref(self, ref, node):
        node['ref'] = self.ref = ref

    def track(self):
        # If self.tracking is not specified it's not an error, just silently return
        if not self.tracking:
            return None

        self.ensure()
        remote_name = self.ensure_remote(self.url)
        with self.timed_activity("Fetching tracking ref '{}' from origin: {}"
                                 .format(self.tracking, self.url)):
            try:
                _ostree.fetch(self.repo, remote=remote_name, ref=self.tracking, progress=self.progress)
            except OSTreeError as e:
                raise SourceError("{}: Failed to fetch tracking ref '{}' from origin {}\n\n{}"
                                  .format(self, self.tracking, self.url, e)) from e

        return self._checksum(self.repo, self.tracking)

    def fetch(self):
        self.ensure()
        remote_name = self.ensure_remote(self.url)
        if not self._exists(self.repo, self.ref):
            with self.timed_activity("Fetching remote ref: {} from origin: {}"
                                     .format(self.ref, self.url)):
                try:
                    _ostree.fetch(self.repo, remote=remote_name, ref=self.ref, progress=self.progress)
                except OSTreeError as e:
                    raise SourceError("{}: Failed to fetch ref '{}' from origin: {}\n\n{}"
                                      .format(self, self.ref, self.url, e)) from e

    def stage(self, directory):
        self.ensure()

        # Checkout self.ref into the specified directory
        with self.tempdir() as tmpdir:
            checkoutdir = os.path.join(tmpdir, 'checkout')

            with self.timed_activity("Staging ref: {} from origin: {}"
                                     .format(self.ref, self.url)):
                try:
                    self._checkout(self.repo, checkoutdir, self.ref, user=True)
                except SourceError as e:
                    raise SourceError("{}: Failed to checkout ref '{}' from origin: {}\n\n{}"
                                      .format(self, self.ref, self.url, e)) from e

            # The target directory is guaranteed to exist, here we must move the
            # content of out checkout into the existing target directory.
            #
            # We may not be able to create the target directory as its parent
            # may be readonly, and the directory itself is often a mount point.
            #
            try:
                for entry in os.listdir(checkoutdir):
                    source_path = os.path.join(checkoutdir, entry)
                    shutil.move(source_path, directory)
            except (shutil.Error, OSError) as e:
                raise SourceError("{}: Failed to move ostree checkout {} from '{}' to '{}'\n\n{}"
                                  .format(self, self.url, tmpdir, directory, e)) from e

    def get_consistency(self):
        if self.ref is None:
            return Consistency.INCONSISTENT

        self.ensure()
        if self._exists(self.repo, self.ref):
            return Consistency.CACHED
        return Consistency.RESOLVED

    #
    # Local helpers
    #
    def ensure(self):
        if not self.repo:
            self.status("Creating local mirror for {}".format(self.url))

            # create also succeeds on existing repository
            repo = OSTree.Repo.new(Gio.File.new_for_path(self.mirror))
            mode = OSTree.RepoMode.ARCHIVE_Z2

            repo.create(mode)

            # Disble OSTree's built in minimum-disk-space check.
            config = repo.copy_config()
            config.set_string('core', 'min-free-space-percent', '0')
            repo.write_config(config)
            repo.reload_config()

            self.repo = repo

    def ensure_remote(self, url):
        if self.original_url == self.url:
            remote_name = 'origin'
        else:
            remote_name = utils.url_directory_name(url)

        gpg_key = None
        if self.gpg_key_path:
            gpg_key = 'file://' + self.gpg_key_path

        try:
            _ostree.configure_remote(self.repo, remote_name, url, key_url=gpg_key)
        except OSTreeError as e:
            raise SourceError("{}: Failed to configure origin {}\n\n{}".format(self, self.url, e)) from e
        return remote_name

    def progress(self, percent, message):
        self.status(message)


    # _checksum():
    #
    # Returns the commit checksum for a given symbolic ref,
    # which might be a branch or tag. If it is a branch,
    # the latest commit checksum for the given branch is returned.
    #
    # Args:
    #    repo (OSTree.Repo): The repo
    #    ref (str): The symbolic ref
    #
    # Returns:
    #    (str): The commit checksum, or None if ref does not exist.
    #
    def _checksum(self, repo, ref):
        _, checksum_ = repo.resolve_rev(ref, True)
        return checksum_



    # _checkout()
    #
    # Checkout the content at 'commit' from 'repo' in
    # the specified 'path'
    #
    # Args:
    #    repo (OSTree.Repo): The repo
    #    path (str): The checkout path
    #    commit_ (str): The commit checksum to checkout
    #    user (boot): Whether to checkout in user mode
    #
    def _checkout(self, repo, path, commit_, user=False):

        # Check out a full copy of an OSTree at a given ref to some directory.
        #
        # Note: OSTree does not like updating directories inline/sync, therefore
        # make sure you checkout to a clean directory or add additional code to support
        # union mode or (if it exists) file replacement/update.
        #
        # Returns True on success
        #
        # cli exmaple:
        #   ostree --repo=repo checkout --user-mode runtime/org.freedesktop.Sdk/x86_64/1.4 foo
        os.makedirs(os.path.dirname(path), exist_ok=True)

        options = OSTree.RepoCheckoutAtOptions()

        # For repos which contain root owned files, we need
        # to checkout with OSTree.RepoCheckoutMode.USER
        #
        # This will reassign uid/gid and also munge the
        # permission bits a bit.
        if user:
            options.mode = OSTree.RepoCheckoutMode.USER

        # Using AT_FDCWD value from fcntl.h
        #
        # This will be ignored if the passed path is an absolute path,
        # if path is a relative path then it will be appended to the
        # current working directory.
        AT_FDCWD = -100
        try:
            repo.checkout_at(options, AT_FDCWD, path, commit_)
        except GLib.GError as e:
            raise SourceError("Failed to checkout commit '{}': {}".format(commit_, e.message)) from e


    # _exists():
    #
    # Checks wether a given commit or symbolic ref exists and
    # is locally cached in the specified repo.
    #
    # Args:
    #    repo (OSTree.Repo): The repo
    #    ref (str): A commit checksum or symbolic ref
    #
    # Returns:
    #    (bool): Whether 'ref' is valid in 'repo'
    #
    def _exists(self, repo, ref):

        # Get the commit checksum, this will:
        #
        #  o Return a commit checksum if ref is a symbolic branch
        #  o Return the same commit checksum if ref is a valid commit checksum
        #  o Return None if the ostree repo doesnt know this ref.
        #
        ref = checksum(repo, ref)
        if ref is None:
            return False

        # If we do have a ref which the ostree knows about, this does
        # not mean we necessarily have the object locally (we may just
        # have some metadata about it, this can happen).
        #
        # Use has_object() only with a resolved valid commit checksum
        # to check if we actually have the object locally.
        _, has_object = repo.has_object(OSTree.ObjectType.COMMIT, ref, None)
        return has_object



# Plugin entry point
def setup():
    return OSTreeSource

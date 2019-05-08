#
#  Copyright (C) 2017 Codethink Limited
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
#        Jürg Billeter <juerg.billeter@codethink.co.uk>
#        Andrew Leeming <andrew.leeming@codethink.co.uk>
#        Tristan Van Berkom <tristan.vanberkom@codethink.co.uk>
#
# Code based on Jürg's artifact cache and Andrew's ostree plugin
#

import os

import gi
from gi.repository.GLib import Variant, VariantDict
from buildstream import SourceError

gi.require_version('OSTree', '1.0')
from gi.repository import GLib, Gio, OSTree  # noqa


# For users of this file, they must expect (except) it.
class OSTreeError(SourceError):
    def __init__(self, message, reason=None):
        super().__init__(message, reason=reason)


# fetch()
#
# Fetch new objects from a remote, if configured
#
# Args:
#    repo (OSTree.Repo): The repo
#    remote (str): An optional remote name, defaults to 'origin'
#    ref (str): An optional ref to fetch, will reduce the amount of objects fetched
#    progress (callable): An optional progress callback
#
# Note that a commit checksum or a branch reference are both
# valid options for the 'ref' parameter. Using the ref parameter
# can save a lot of bandwidth but mirroring the full repo is
# still possible.
#
def fetch(repo, remote="origin", ref=None, progress=None):
    # Fetch metadata of the repo from a remote
    #
    # cli example:
    #  ostree --repo=repo pull --mirror freedesktop:runtime/org.freedesktop.Sdk/x86_64/1.4
    def progress_callback(info):
        status = async_progress.get_status()
        outstanding_fetches = async_progress.get_uint('outstanding-fetches')
        bytes_transferred = async_progress.get_uint64('bytes-transferred')
        fetched = async_progress.get_uint('fetched')
        requested = async_progress.get_uint('requested')

        if status:
            progress(0.0, status)
        elif outstanding_fetches > 0:
            formatted_bytes = GLib.format_size_full(bytes_transferred, 0)
            if requested == 0:
                percent = 0.0
            else:
                percent = (fetched * 1.0 / requested) * 100

            progress(percent,
                     "Receiving objects: {:d}% ({:d}/{:d}) {}".format(int(percent), fetched,
                                                                      requested, formatted_bytes))
        else:
            progress(100.0, "Writing Objects")

    async_progress = None
    if progress is not None:
        async_progress = OSTree.AsyncProgress.new()
        async_progress.connect('changed', progress_callback)

    # FIXME: This hangs the process and ignores keyboard interrupt,
    #        fix this using the Gio.Cancellable
    refs = None
    if ref is not None:
        refs = [ref]

    try:
        repo.pull(remote,
                  refs,
                  OSTree.RepoPullFlags.MIRROR,
                  async_progress,
                  None)  # Gio.Cancellable
    except GLib.GError as e:
        if ref is not None:
            raise OSTreeError("Failed to fetch ref '{}' from '{}': {}".format(ref, remote, e.message)) from e
        else:
            raise OSTreeError("Failed to fetch from '{}': {}".format(remote, e.message)) from e


# configure_remote():
#
# Ensures a remote is setup to a given url.
#
# Args:
#    repo (OSTree.Repo): The repo
#    remote (str): The name of the remote
#    url (str): The url of the remote ostree repo
#    key_url (str): The optional url of a GPG key (should be a local file)
#
def configure_remote(repo, remote, url, key_url=None):
    # Add a remote OSTree repo. If no key is given, we disable gpg checking.
    #
    # cli exmaple:
    #   wget https://sdk.gnome.org/keys/gnome-sdk.gpg
    #   ostree --repo=repo --gpg-import=gnome-sdk.gpg remote add freedesktop https://sdk.gnome.org/repo
    options = None  # or GLib.Variant of type a{sv}
    if key_url is None:
        vd = VariantDict.new()
        vd.insert_value('gpg-verify', Variant.new_boolean(False))
        options = vd.end()

    try:
        repo.remote_change(None,      # Optional OSTree.Sysroot
                           OSTree.RepoRemoteChange.ADD_IF_NOT_EXISTS,
                           remote,    # Remote name
                           url,       # Remote url
                           options,   # Remote options
                           None)      # Optional Gio.Cancellable
    except GLib.GError as e:
        raise OSTreeError("Failed to configure remote '{}': {}".format(remote, e.message)) from e

    # Remote needs to exist before adding key
    if key_url is not None:
        try:
            gfile = Gio.File.new_for_uri(key_url)
            stream = gfile.read()
            repo.remote_gpg_import(remote, stream, None, 0, None)
        except GLib.GError as e:
            raise OSTreeError("Failed to add gpg key from url '{}': {}".format(key_url, e.message)) from e

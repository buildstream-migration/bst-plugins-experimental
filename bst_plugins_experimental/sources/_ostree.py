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

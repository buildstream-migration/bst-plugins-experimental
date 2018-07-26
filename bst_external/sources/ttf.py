#  Copyright (C) 2017 Codethink Limited
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Thomas Coldrick <thomas.coldrick@codethink.co.uk>

"""
ttf - stage ttf files from remote sources
=========================================

**Usage:**

.. code:: yaml

   # Specify the ttf source kind
   kind: ttf

   # Optionally specify a relative staging directory
   # directory: path/to/stage

   # Specify the ttf url. Using an alias defined in your project
   # configuration is encouraged. 'bst track' will update the
   # sha256sum in 'ref' to the downloaded file's sha256sum.
   url: upstream:foo.ttf

   # Specify the ref. It's a sha256sum of the file you download.
   ref: 6c9f6f68a131ec6381da82f2bff978083ed7f4f7991d931bfa767b7965ebc94b

"""

import os
import urllib.request
import urllib.error
import contextlib
import shutil

from buildstream import Source, SourceError, Consistency
from buildstream import utils


class TtfSource(Source):
    # pylint: disable=attribute-defined-outside-init

    COMMON_CONFIG_KEYS = Source.COMMON_CONFIG_KEYS + ['url', 'ref', 'etag']

    def configure(self, node):
        self.original_url = self.node_get_member(node, str, 'url')
        self.ref = self.node_get_member(node, str, 'ref', None)
        self.url = self.translate_url(self.original_url)
        self.name = self.url.split('/')[-1]
        self._warn_deprecated_etag(node)

    def preflight(self):
        return

    def get_unique_key(self):
        return [self.original_url, self.ref]

    def get_consistency(self):
        if self.ref is None:
            return Consistency.INCONSISTENT

        if os.path.isfile(self._get_mirror_file()):
            return Consistency.CACHED

        else:
            return Consistency.RESOLVED

    def load_ref(self, node):
        self.ref = self.node_get_member(node, str, 'ref', None)
        self._warn_deprecated_etag(node)

    def get_ref(self):
        return self.ref

    def set_ref(self, ref, node):
        node['ref'] = self.ref = ref

    def stage(self, directory):
        try:
            ttf = self._get_mirror_file()
            utils.safe_copy(ttf, os.path.join(directory, self.name))
        except OSError as e:
            raise SourceError("{}: Error staging source: {}".format(self, e)) from e

    def track(self):
        # there is no 'track' field in the source to determine what/whether
        # or not to update refs, because tracking a ref is always a conscious
        # decision by the user.
        with self.timed_activity("Tracking {}".format(self.url),
                                 silent_nested=True):
            new_ref = self._ensure_mirror()

            if self.ref and self.ref != new_ref:
                detail = "When tracking, new ref differs from current ref:\n" \
                    + "  Tracked URL: {}\n".format(self.url) \
                    + "  Current ref: {}\n".format(self.ref) \
                    + "  New ref: {}\n".format(new_ref)
                self.warn("Potential man-in-the-middle attack!", detail=detail)

            return new_ref

    def fetch(self):

        # Just a defensive check, it is impossible for the
        # file to be already cached because Source.fetch() will
        # not be called if the source is already Consistency.CACHED.
        #
        if os.path.isfile(self._get_mirror_file()):
            return  # pragma: nocover

        # Download the file, raise hell if the sha256sums don't match,
        # and mirror the file otherwise.
        with self.timed_activity("Fetching {}".format(self.url), silent_nested=True):
            sha256 = self._ensure_mirror()
            if sha256 != self.ref:
                raise SourceError("File downloaded from {} has sha256sum '{}', not '{}'!"
                                  .format(self.url, sha256, self.ref))

    def _warn_deprecated_etag(self, node):
        etag = self.node_get_member(node, str, 'etag', None)
        if etag:
            provenance = self.node_provenance(node, member_name='etag')
            self.warn('{} "etag" is deprecated and ignored.'.format(provenance))

    def _get_etag(self, ref):
        etagfilename = os.path.join(self._get_mirror_dir(), '{}.etag'.format(ref))
        if os.path.exists(etagfilename):
            with open(etagfilename, 'r') as etagfile:
                return etagfile.read()

        return None

    def _store_etag(self, ref, etag):
        etagfilename = os.path.join(self._get_mirror_dir(), '{}.etag'.format(ref))
        with utils.save_file_atomic(etagfilename) as etagfile:
            etagfile.write(etag)

    def _ensure_mirror(self):
        # Downloads from the url and caches it according to its sha256sum.
        try:
            with self.tempdir() as td:
                default_name = os.path.basename(self.url)
                request = urllib.request.Request(self.url)
                request.add_header('Accept', '*/*')

                # We do not use etag in case what we have in cache is
                # not matching ref in order to be able to recover from
                # corrupted download.
                if self.ref:
                    etag = self._get_etag(self.ref)

                    # Do not re-download the file if the ETag matches.
                    if etag and self.get_consistency() == Consistency.CACHED:
                        request.add_header('If-None-Match', etag)

                with contextlib.closing(urllib.request.urlopen(request)) as response:
                    info = response.info()

                    etag = info['ETag'] if 'ETag' in info else None

                    filename = info.get_filename(default_name)
                    filename = os.path.basename(filename)
                    local_file = os.path.join(td, filename)
                    with open(local_file, 'wb') as dest:
                        shutil.copyfileobj(response, dest)

                # Make sure url-specific mirror dir exists.
                if not os.path.isdir(self._get_mirror_dir()):
                    os.makedirs(self._get_mirror_dir())

                # Store by sha256sum
                sha256 = utils.sha256sum(local_file)
                # Even if the file already exists, move the new file over.
                # In case the old file was corrupted somehow.
                os.rename(local_file, self._get_mirror_file(sha256))

                if etag:
                    self._store_etag(sha256, etag)
                return sha256

        except urllib.error.HTTPError as e:
            if e.code == 304:
                # 304 Not Modified.
                # Because we use etag only for matching ref, currently specified ref is what
                # we would have downloaded.
                return self.ref
            raise SourceError("{}: Error mirroring {}: {}"
                              .format(self, self.url, e)) from e

        except (urllib.error.URLError, urllib.error.ContentTooShortError, OSError) as e:
            raise SourceError("{}: Error mirroring {}: {}"
                              .format(self, self.url, e)) from e

    def _get_mirror_dir(self):
        return os.path.join(self.get_mirror_directory(),
                            utils.url_directory_name(self.original_url))

    def _get_mirror_file(self, sha=None):
        return os.path.join(self._get_mirror_dir(), sha or self.ref)

def setup():
    return TtfSource

# Copyright (c) 2018 freedesktop-sdk
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors:
#        Thomas Coldrick <thomas.coldrick@codethink.co.uk>


"""
tar_element - Output tarballs
=============================

An element plugin for creating tarballs from the specified
dependencies

Default Configuration
~~~~~~~~~~~~~~~~~~~~~

The tarball_element default configuration:
  .. literalinclude:: ../../../bst_external/elements/tar_element.yaml
     :language: yaml
"""

import tarfile
import os

from buildstream import Element, Scope, ElementError

class TarElement(Element):

    # The tarball's output is its dependencies, so
    # we must rebuild if they change
    BST_STRICT_REBUILD = True

    # Tarballs don't need runtime dependencies
    BST_FORBID_RDEPENDS = True

    # Our only sources are previous elements, so we forbid
    # remote sources
    BST_FORBID_SOURCES = True

    def configure(self, node):
        self.node_validate(node, [
            'filename', 'compression'
        ])
        self.filename = self.node_subst_member(node, 'filename')
        self.compression = self.node_get_member(node, str, 'compression')

        if self.compression not in ['none', 'gzip', 'xz', 'bzip2']:
            raise ElementError("{}: Invalid compression option {}".format(self, self.compression))

    def preflight(self):
        pass

    def get_unique_key(self):
        key = {}
        key['filename'] = self.filename
        key['compression'] = self.compression
        return key

    def configure_sandbox(self, sandbox):
        pass

    def stage(self, sandbox):
        pass

    def assemble(self, sandbox):
        basedir = sandbox.get_directory()
        inputdir = os.path.join(basedir, 'input')
        outputdir = os.path.join(basedir, 'output')
        os.makedirs(inputdir, exist_ok=True)
        os.makedirs(outputdir, exist_ok=True)

        # Stage deps in the sandbox root
        with self.timed_activity('Staging dependencies', silent_nested=True):
            self.stage_dependency_artifacts(sandbox, Scope.BUILD, path='/input')

        with self.timed_activity('Creating tarball', silent_nested=True):

            # Create an uncompressed tar archive
            compress_map = {'none': '', 'gzip': 'gz', 'xz': 'xz', 'bzip2':'bz2'}
            extension_map = {'none': '.tar', 'gzip': '.tar.gz', 'xz': '.tar.xz', 'bzip2': '.tar.bz2'}
            tarname = os.path.join(outputdir, self.filename + extension_map[self.compression])
            mode = 'w:' + compress_map[self.compression]
            with tarfile.TarFile.open(name=tarname, mode=mode) as tar:
                for f in os.listdir(inputdir):
                    tar.add(os.path.join(inputdir, f), arcname=f)

        return '/output'

def setup():
    return TarElement

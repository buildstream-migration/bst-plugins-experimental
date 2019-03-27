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
#        Valentin David <valentin.david@gmail.com>
#        Adam Jones <adam.jones@codethink.co.uk>

import os
import re
import json
from collections import OrderedDict
from buildstream import Element, ElementError, Scope

"""
Collect Manifest Element

A buildstream plugin used to produce a manifest file
containing a list of elements for a given dependency.

The manifest contains useful information such as:
    - CPE data, such as CVE patches
    - Package name
    - Version
    - Sources
     - Source locations
     - SHAs
     - Patch files

The manifest file is exported as a json file to the path provided
under the "path" variable defined in the .bst file.
"""

def get_version(sources):
    """
    This function attempts to extract the source version
    from a dependency. This data can generally be found
    in the url for tar balls, or the ref for git repos.

    :sources A list of BuildStream Sources
    """
    for source in sources:
        if source.get_kind() in ['tar', 'zip']:
            url = source.url
            filename = url.rpartition('/')[2]
            match = re.search(r'(\d+\.\d+(?:\.\d+)?)', filename)
            if match:
                return match.groups()[-1]
        elif source.get_kind() in ['git', 'git_tag']:
            ref = source.mirror.ref
            match = re.search(r'(\d+\.\d+(?:\.\d+)?)', ref)
            if match:
                return match.groups()[-1]

def get_source_locations(sources):
    """
    Returns a list of source URLs and refs, currently for
    git, tar and patch sources.

    :sources A list of BuildStream Sources
    """
    source_locations = []
    for source in sources:
        if source.get_kind() in ['git']:
            url = source.translate_url(source.mirror.url, alias_override=None,
                                                                primary=source.mirror.primary)
            source_locations.append({"type": source.get_kind(), "url" : url, "commit" : source.mirror.ref})
        if source.get_kind() in ['git_tag']:
            url = source.translate_url(source.mirror.url, alias_override=None,
                                                                primary=source.mirror.primary)
            source_locations.append({"type": "git", "x-bst-kind": source.get_kind(), "url" : url, "commit" : source.mirror.ref})
        if source.get_kind() in ['patch']:
            patch = source.path.rpartition('/')[2]
            source_locations.append({"type": source.get_kind(), "path": patch})
        if source.get_kind() in ['tar', 'zip']:
            source_locations.append({"type": "archive", "url": source.url, "sha256": source.ref})

    return source_locations

def cleanup_provenance(data):
    """
    Remove buildstream provenance data from the output data
    """
    if isinstance(data, dict):
        ret = OrderedDict()
        for k, v in data.items():
            if k != '__bst_provenance_info':
                ret[k] = cleanup_provenance(v)
        return ret
    elif isinstance(data, list):
        return [cleanup_provenance(v) for v in data]
    else:
        return data

class CollectManifestElement(Element):

    BST_FORMAT_VERSION = 1

    def configure(self, node):
        if 'path' in node:
            self.path = self.node_subst_member(node, 'path', None)
        else:
            self.path = None

    def preflight(self):
        pass

    def get_unique_key(self):
        key = {
            'path': self.path
        }
        return key

    def configure_sandbox(self, sandbox):
        pass

    def stage(self, sandbox):
        pass

    def extract_cpe(self, dep):
        cpe = dep.get_public_data('cpe')

        sources = list(dep.sources())

        if cpe is None:
            cpe = {}

        if 'product' not in cpe:
            cpe['product'] = os.path.basename(os.path.splitext(dep.name)[0])

        if 'version' not in cpe:
            version = get_version(sources)

            if version is None:
                self.status('Missing version to {}. Please add variable "manifest-version"'.format(dep))

            if version:
                cpe['version'] = version

        return cpe

    def extract_sources(self, dep):
        sources = list(dep.sources())

        source_locations = []

        if sources:
            source_locations = get_source_locations(sources)

        return source_locations

    def get_dependencies(self, dep, visited):
        if dep in visited:
            return
        visited.add(dep)
        for subdep in dep.dependencies(Scope.RUN, recurse=False):
            yield from self.get_dependencies(subdep, visited)
        yield dep

    def assemble(self, sandbox):
        manifest = OrderedDict()
        manifest['//NOTE'] = 'This is a generated manifest from buildstream files and not usable by flatpak-builder'
        manifest['modules'] = []

        visited = set()
        for top_dep in self.dependencies(Scope.BUILD,
                                         recurse=False):
            for dep in self.get_dependencies(top_dep, visited):
                import_manifest = dep.get_public_data('cpe-manifest')

                if import_manifest:
                    manifest['modules'].extend(import_manifest['modules'])
                else:
                    cpe = self.extract_cpe(dep)
                    sources = self.extract_sources(dep)

                    if cpe:
                        manifest['modules'].append({'name': dep.name,
                                                    'x-cpe': cpe,
                                                    'sources': sources})

        if self.path:
            basedir = sandbox.get_directory()
            path = os.path.join(basedir, self.path.lstrip(os.path.sep))
            if os.path.isfile(path):
                if path[-1].isdigit():
                    version = int(path[-1]) + 1
                    new_path = list(path)
                    new_path[-1] = str(version)
                    path = ''.join(new_path)
                else:
                    path = path + '-1'
            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, 'w') as o:
                json.dump(cleanup_provenance(manifest), o, indent=2)

        self.set_public_data('cpe-manifest', manifest)
        return os.path.sep

    def get_unique_key(self):
        return self.BST_FORMAT_VERSION


def setup():
    return CollectManifestElement

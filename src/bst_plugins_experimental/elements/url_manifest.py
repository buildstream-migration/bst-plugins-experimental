# Copyright (c) 2020 freedesktop-sdk
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
#     collect_manifest authors:
#         Valentin David <valentin.david@gmail.com>
#         Adam Jones <adam.jones@codethink.co.uk>
#     url_manifest author:
#         Douglas Winship <douglas.winship@codethink.co.uk> (Url Manifest)
#
#     (The url_manifest plugin is a modified derivative of the collect_manifest
#     plugin, released under the same license.)

"""Url Manifest Element

A buildstream plugin used to produce a manifest file listing source url
information for a list of elements, and for all their dependencies and their
subdependencies, all the way down to the bottom of the tree.

The manifest contains information such as:
    - the name of the each sub-dependency
    - the alias used in the url (null if no alias is used)
    - the 'main' source url

In future, we'd also like to include the list of the download mirrors for each
source url (as defined by any mirror-aliases listed in project.conf).
Unfortunately it's not currently possible to do that from a plugin without using
protected/private functions.


#### Usage:

Dependencies:
  
  Anything listed as a dependency of the url_manifest element, will
  be added to the manifest (along with all its dependencies and
  subdependencies).

  You can add multiple dependencies, and they will all be included in the
  manifest. However, one url_manifest element will only ever produce one json
  manifest. If you want separate manifests for separate elements, you'll need to
  use a different url_manifest element for each one.

  The manifest will include all dependencies and subdependencies, recursively.
  That includes build dependencies, and build dependencies of build
  dependencies, etc.

  Target elements can be added to the url_manifest element as build dependencies
  or as runtime dependencies; both will be included in the manifest. However,
  build dependencies are more likely to make sense. The build artifact isn't
  software, so there's not likely to be any good reason for it to need runtime
  dependencies.

Configuration:

  The manifest will be exported in the build artifact, as a json file. The
  desired path for the manifest file (including filename) should be specified
  under "config: path:" eg:

      config:
        path: "/my_dir1/my_dir2/my-filename.json"

  or just:

      config:
        path: "url-manifest.json"

Output-format:

  The json manifest consists of a list of elements, where each element is
  represented as a dictionary with two key-value pairs: "element" (the filename
  of an element's bst file) and "sources" (a list of that element's sources).

  url_manifest can only recognize specific kinds of source. If a source isn't a
  recognized type, then it won't appear in the manifest. Similarly, if an
  element has no sources (or no recognized sources) then the element will not
  appear in the manifest either (ie, you will never see in the manifest any
  elements that have an empty source list).

  For instance, a stack element will have no sources, but its dependencies
  generally will. Therefore the manifest won't include the stack element, but it
  will probably include many of the stack element's dependencies and
  sub-dependencies.

Recognized sources:

  Currently, url_manifest can recognize the following kinds of source:
    # cargo
    # git
    # git_tag
    # ostree
    # tar 
    # zip
    # remote

  More source kinds could be added in future. However, source kinds will only be
  added if they involve fetching data from a url. 'Local' sources, for instance.
  are intentionally not included.

Fields:

  Each element dictionary contains a 'sources' list, and inside that list each
  source is represented as a dictionary. Source dictionaires have the
  following fields:

  [All sources:]

  kind:       the source kind (taken directly from the source kind)
              eg: "git_tag"

  raw_url:    the url as written in the bst file, before alias-substitution
              eg: "savannah:config.git"

  alias:      the alias used in the raw url. A null value if no alias is used.
              eg: "savannah"

  source_url: the url after alias substitution (ie the actual url of the
              resource) eg: "https://git.savannah.gnu.org/git/config.git"
  
  [Some sources:]

  ref:  taken from the source's ref field in the bst file (if there is one).
  tag:  the tag of the commit, if there is one (git and git_tag only). Taken
        from the ref.
  
Duplicates:

  The same element is not expected to appear in the list more than once. However
  this is not guaranteed. (elements are not (usually) duplicated.)

  If the same source url is listed in more than one element, it will appear in
  the manifest more than once. (sources may be duplicated.)

  Cargo sources can list multiple different crates, all under one heading.
  Buildstream recognizes this as a single source, however it involves multiple
  urls which is a challenge for this plugin. To handle this, the url_manifest
  plugin will treat each crate as if it were a separate source, in order to
  preserve the "one url per source" format of the manifest.
"""

import json
import os
import re
from buildstream import Element, Scope

def get_source_locations(sources):
    """
    Returns a list of source URLs and refs, currently for
    cargo, git, git_tag, tar, ostree, remote, zip and tar sources.
    Patch sources and local sources are not included in the ouput,
    since they don't have source URLs

    :sources A list or generator of BuildStream Sources
    """
    source_locations = []
    for source in sources:
        source_kind = source.get_kind()
        if source_kind == 'cargo':
            raw_cargo_url = source.url
            cargo_alias = raw_cargo_url.split(':', 1)[0]
            base_cargo_url = source.translate_url(source.url)
            for crate in source.ref:
                rest_of_url = '/{}/{}-{}.crate'.format(
                    crate['name'], crate['name'], crate['version']
                )
                source_locations.append({
                    'kind': 'cargo',
                    'alias': cargo_alias,
                    'raw_url': raw_cargo_url + rest_of_url,
                    'source_url': base_cargo_url + rest_of_url,
                })
        if source_kind in ['git', 'git_tag', 'ostree', 'tar', 'zip', 'remote']:
            #skip over sources that don't have source URLs, like patch sources
            if source_kind in ['tar', 'zip', 'remote', 'ostree']:
                source_url = source.url
            if source_kind in ['git', 'git_tag']:
                source_url = source.translate_url(
                    source.original_url,
                    alias_override=None,
                    primary=source.mirror.primary
                )

            raw_url = source.original_url
            if source_url == raw_url:
                # no alias detected, no translation done
                alias = None
            else:
                # the system must have recognised an alias, therefore...
                # ...everything before the first colon is the alias
                # This would be easier if source._get_alias() wasn't a protected part of the class
                alias = raw_url.split(':', 1)[0]


            source_dict = {
                'kind': source_kind,
                'alias' : alias,
                'raw_url' : raw_url,
                'source_url' : source_url,
            }
            if source_kind == 'ostree':
                source_dict['ref'] = source.ref
            if source_kind in ['git', 'git_tag']:
                source_dict['ref'] = source.mirror.ref
                m = re.match(r'(?P<tag>.*)-[0-9]+-g(?P<ref>.*)', source.mirror.ref)
                if m:
                    source_dict['tag'] = m.group('tag')
                else:
                    source_dict['tag'] = None
            source_locations.append(source_dict)

    return source_locations


class UrlManifestElement(Element):

    BST_FORMAT_VERSION = 0.2

    def configure(self, node):
        if 'path' in node:
            self.path = self.node_subst_member(node, 'path', None)
        else:
            self.path = None

    def preflight(self):
        pass

    def get_unique_key(self):
        key = {
            'path': self.path,
            'version': self.BST_FORMAT_VERSION
        }
        return key

    def configure_sandbox(self, sandbox):
        pass

    def stage(self, sandbox):
        pass

    def assemble(self, sandbox):
        manifest = []
        visited_names_list = []

        for dep in self.dependencies(Scope.ALL, recurse=True):
            #de-duplicate list (some elements in some cases seem to get listed multiple times)
            if dep.name in visited_names_list:
                continue
            visited_names_list.append(dep.name)

            sources = get_source_locations(dep.sources())
            if sources:
                manifest.append({
                    'element': dep.name, 'sources': sources})

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

            with open(path, 'w') as open_file:
                json.dump(manifest, open_file, indent=2)

        return os.path.sep

def setup():
    return UrlManifestElement

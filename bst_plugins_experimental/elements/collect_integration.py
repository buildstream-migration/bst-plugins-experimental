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


"""Collect Integration Element

A buildstream plugin used to collect the integration
commands of all its dependencies, and compose them
into a single shell script.

Used to generate freedesktop-post.sh
"""
import os
import stat
from buildstream import Element, ElementError, Scope

class ExtractIntegrationElement(Element):
    def configure(self, node):
        self.node_validate(node, [
            'script-path',
            'ignore'
        ])

        self.script_path = self.node_subst_member(node, 'script-path')
        self.ignore = self.node_get_member(node, list, 'ignore', [])

    def preflight(self):
        runtime_deps = list(self.dependencies(Scope.RUN, recurse=False))
        if runtime_deps:
            raise ElementError("{}: Only build type dependencies supported by collect-integration elements"
                               .format(self))

        sources = list(self.sources())
        if sources:
            raise ElementError("{}: collect-integration elements may not have sources".format(self))

        for ignore in self.ignore:
            if self.search(Scope.BUILD, ignore) is None:
                raise ElementError("{}: element {} is not in dependencies".format(self, ignore))

    def get_unique_key(self):
        key = {
            'script-path': self.script_path,
            'ignore': set(self.ignore)
        }
        return key

    def configure_sandbox(self, sandbox):
        pass

    def stage(self, sandbox):
        pass

    def assemble(self, sandbox):
        basedir = sandbox.get_directory()
        script_path = os.path.join(basedir, self.script_path.lstrip(os.path.sep))
        os.makedirs(os.path.dirname(script_path), exist_ok=True)

        def opener(path, flags):
            return os.open(path, flags, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        ignore_set = set()
        for ignore in self.ignore:
            ignore_set.add(self.search(Scope.BUILD, ignore))

        with open(script_path, 'w', opener=opener) as f:
            f.write('#!/bin/sh\n')
            f.write('set -e\n\n')
            for dependency in self.dependencies(Scope.BUILD):
                if dependency in ignore_set:
                    continue
                bstdata = dependency.get_public_data('bst')
                if bstdata is not None:
                    commands = dependency.node_get_member(bstdata, list, 'integration-commands', [])
                    if commands:
                        f.write('# integration commands from {}\n'.format(dependency.name))
                    for i in range(len(commands)):
                        cmd = dependency.node_subst_list_element(bstdata, 'integration-commands', [i])

                        f.write('{}\n\n'.format(cmd))

        return os.path.sep

def setup():
    return ExtractIntegrationElement

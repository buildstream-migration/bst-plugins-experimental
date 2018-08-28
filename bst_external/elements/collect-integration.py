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
            'script-path'
        ])

        self.script_path = self.node_subst_member(node, 'script-path')

    def preflight(self):
        runtime_deps = list(self.dependencies(Scope.RUN, recurse=False))
        if runtime_deps:
            raise ElementError("{}: Only build type dependencies supported by flatpak-image elements"
                               .format(self))

        sources = list(self.sources())
        if sources:
            raise ElementError("{}: flatpak-image elements may not have sources".format(self))

    def get_unique_key(self):
        key = {
            'script-path': self.script_path
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

        with open(script_path, 'w', opener=opener) as f:
            f.write('#!/bin/sh\n')
            f.write('set -e\n\n')
            for dependency in self.dependencies(Scope.BUILD):
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

#
#  Copyright (C) 2016 Codethink Limited
#  Copyright (C) 2018 Bloomberg Finance LP
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
#        Tristan Van Berkom <tristan.vanberkom@codethink.co.uk>
"""
BazelElement - Element plugin for Bazel builds
================================================
Basic element for building using the bazel build system. This is pretty much
just a BuildElement for now, but this will change as time goes on.
"""

import os

from buildstream import Element, SandboxFlags, Scope


_command_steps = ['configure-commands',
                  'build-commands',
                  'install-commands']


class BazelElement(Element):

    #############################################################
    #             Abstract Method Implementations               #
    #############################################################
    def configure(self, node):

        self.__commands = {}  # pylint: disable=attribute-defined-outside-init

        # FIXME: Currently this forcefully validates configurations
        #        for all BuildElement subclasses so they are unable to
        #        extend the configuration
        node.validate_keys(_command_steps)

        for command_name in _command_steps:
            self.__commands[command_name] = self.__get_commands(node, command_name)

    def preflight(self):
        pass

    def get_unique_key(self):
        dictionary = {}

        for command_name, command_list in self.__commands.items():
            dictionary[command_name] = command_list

        # Specifying notparallel for a given element effects the
        # cache key, while having the side effect of setting max-jobs to 1,
        # which is normally automatically resolved and does not affect
        # the cache key.
        if self.get_variable('notparallel'):
            dictionary['notparallel'] = True

        return dictionary

    def configure_sandbox(self, sandbox):
        build_root = self.get_variable('build-root')
        install_root = self.get_variable('install-root')

        # Tell the sandbox to mount the build root and install root
        sandbox.mark_directory(build_root)
        sandbox.mark_directory(install_root)

        # Ensure the home directory exists
        sandbox.mark_directory('/home')

        # Ensure /dev/shm exists
        sandbox.mark_directory('/dev/shm')

        # Allow running all commands in a specified subdirectory
        command_subdir = self.get_variable('command-subdir')
        if command_subdir:
            command_dir = os.path.join(build_root, command_subdir)
        else:
            command_dir = build_root
        sandbox.set_work_directory(command_dir)

        # Tell sandbox which directory is preserved in the finished artifact
        sandbox.set_output_directory(install_root)

        # Setup environment
        sandbox.set_environment(self.get_environment())

    def stage(self, sandbox):

        # Stage deps in the sandbox root
        with self.timed_activity("Staging dependencies", silent_nested=True):
            self.stage_dependency_artifacts(sandbox, Scope.BUILD)

        # Run any integration commands provided by the dependencies
        # once they are all staged and ready
        with sandbox.batch(SandboxFlags.NONE, label="Integrating sandbox"):
            for dep in self.dependencies(Scope.BUILD):
                dep.integrate(sandbox)

        # Stage sources in the build root
        self.stage_sources(sandbox, self.get_variable('build-root'))

    def assemble(self, sandbox):
        # Run commands
        for command_name in _command_steps:
            commands = self.__commands[command_name]
            if not commands or command_name == 'configure-commands':
                continue

            with sandbox.batch(SandboxFlags.ROOT_READ_ONLY | SandboxFlags.NETWORK_ENABLED,
                               label="Running {}".format(command_name)):
                for cmd in commands:
                    self.__run_command(sandbox, cmd)

        # %{install-root}/%{build-root} should normally not be written
        # to - if an element later attempts to stage to a location
        # that is not empty, we abort the build - in this case this
        # will almost certainly happen.
        staged_build = os.path.join(self.get_variable('install-root'),
                                    self.get_variable('build-root'))

        if os.path.isdir(staged_build) and os.listdir(staged_build):
            self.warn("Writing to %{install-root}/%{build-root}.",
                      detail="Writing to this directory will almost " +
                      "certainly cause an error, since later elements " +
                      "will not be allowed to stage to %{build-root}.")

        # Return the payload, this is configurable but is generally
        # always the /buildstream-install directory
        return self.get_variable('install-root')

    def prepare(self, sandbox):
        commands = self.__commands['configure-commands']
        if commands:
            with sandbox.batch(SandboxFlags.ROOT_READ_ONLY, label="Running configure-commands"):
                for cmd in commands:
                    self.__run_command(sandbox, cmd)

    def generate_script(self):
        script = ""
        for command_name in _command_steps:
            commands = self.__commands[command_name]

            for cmd in commands:
                script += "(set -ex; {}\n) || exit 1\n".format(cmd)

        return script

    #############################################################
    #                   Private Local Methods                   #
    #############################################################
    def __get_commands(self, node, name):
        raw_commands = node.get_sequence(name, [])
        return [
            self.node_subst_vars(command)
            for command in raw_commands
        ]

    def __run_command(self, sandbox, cmd):
        # Note the -e switch to 'sh' means to exit with an error
        # if any untested command fails.
        #
        sandbox.run(['sh', '-c', '-e', cmd + '\n'],
                    SandboxFlags.ROOT_READ_ONLY | SandboxFlags.NETWORK_ENABLED,
                    label=cmd)


def setup():
    return BazelElement

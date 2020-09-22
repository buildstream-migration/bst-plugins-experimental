#  Copyright (C) 2018 Abderrahim Kitouni
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
#        Abderrahim Kitouni <akitouni@gnome.org>

"""flatpak repository element

A `ScriptElement
<https://docs.buildstream.build/master/buildstream.scriptelement.html#module-buildstream.scriptelement>`_
implementation for exporting a flatpak repository from a set of :ref:`flatpack images <flatpak_image>`.

The flatpak_repo default configuration:
  .. literalinclude:: ../../../src/bst_plugins_experimental/elements/flatpak_repo.yaml
     :language: yaml
"""

from buildstream import ScriptElement, ElementError


class FlatpakRepoElement(ScriptElement):
    BST_MIN_VERSION = "2.0"
    BST_ARTIFACT_VERSION = 1
    BST_FORBID_RDEPENDS = True

    def configure(self, node):
        node.validate_keys(["copy-refs", "repo-mode", "arch", "branch"])

        self._copy_refs = []
        for subnode in node.get_sequence("copy-refs"):
            subnode.validate_keys(["src", "dest"])
            self._copy_refs.append(
                (
                    subnode.get_str("src"),
                    subnode.get_str("dest"),
                )
            )

        self._arch = node.get_str("arch")
        self._branch = node.get_str("branch")

        self.set_work_dir()
        self.set_root_read_only(True)

        self._repo_mode = node.get_str("repo-mode")
        self.set_install_root("/buildstream/repo")
        self.add_commands(
            "init repository",
            [
                "ostree init --repo=/buildstream/repo --mode={}".format(
                    self._repo_mode
                )
            ],
        )

    def configure_dependencies(self, dependencies):

        self._flatpaks = []

        for dep in dependencies:
            flatpak_image_dep = False
            flatpak_stack_dep = False

            if dep.config:
                dep.config.validate_keys(["flatpak-image", "flatpak-stack"])
                flatpak_image_dep = dep.config.get_bool("flatpak-image", False)
                flatpak_stack_dep = dep.config.get_bool("flatpak-stack", False)

                if flatpak_image_dep and flatpak_stack_dep:
                    raise ElementError(
                        "{}: Dependency specified as both a flatpak image and a stack".format(
                            dep.config.get_provenance()
                        )
                    )

            if flatpak_image_dep:
                self._layout_flatpak(dep.element, dep.path)
            elif flatpak_stack_dep:
                for flatpak_image in dep.element.dependencies(recurse=False):
                    self._layout_flatpak(
                        flatpak_image, dep.path, is_stack=True
                    )
            else:
                self.layout_add(dep.element, dep.path, "/")

        if not self._flatpaks:
            raise ElementError(
                "{}: No flatpak images specified for this repo".format(self)
            )

        # Add these commands after laying out the flaptaks, which also adds commands.
        #
        for src, dest in self._copy_refs:
            self.add_commands(
                "copy ref {} -> {}".format(src, dest),
                [
                    "flatpak build-commit-from --src-ref={} /buildstream/repo {}".format(
                        src, dest
                    )
                ],
            )

    def _layout_flatpak(self, element, path, is_stack=False):

        # If it is a stack, make a more descriptive identifier for
        # the commands and layout.
        #
        if is_stack:
            path = "{} ({})".format(path, element.name)

        def staging_dir(elt):
            return "/buildstream/input/{}".format(elt.normal_name)

        def export_command(elt):
            return "flatpak build-export --files=files --arch={} /buildstream/repo {} {}".format(
                self._arch, staging_dir(elt), self._branch
            )

        self._flatpaks.append(element)
        self.layout_add(element, path, staging_dir(element))
        self.add_commands("export {}".format(path), [export_command(element)])


# Plugin entry point
def setup():
    return FlatpakRepoElement

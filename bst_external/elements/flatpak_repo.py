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

A :mod:`ScriptElement <buildstream.scriptelement>` implementation for exporting
a flatpak repository from a set of `flatpak_image`s.

The flatpak_repo default configuration:
  .. literalinclude:: ../../../bst_external/elements/flatpak_repo.yaml
     :language: yaml
"""

from buildstream import ScriptElement, Scope, ElementError

class FlatpakRepoElement(ScriptElement):
    def configure(self, node):
        self.node_validate(node, ['environment', 'arch', 'branch'])

        self._env = self.node_get_member(node, list, 'environment')

        self._arch = self.node_subst_member(node, 'arch')
        self._branch = self.node_subst_member(node, 'branch')

        self.set_work_dir()
        self.set_install_root('/buildstream/repo')
        self.set_root_read_only(True)

    def stage(self, sandbox):
        def staging_dir(elt):
            return '/buildstream/input/{}'.format(elt.name)

        def export_command(elt):
            return 'flatpak build-export --files=files --arch={} /buildstream/repo {} {}'\
                .format(self._arch, staging_dir(elt), self._branch)

        env = [self.search(Scope.BUILD, elt) for elt in self._env]

        for elt in self.dependencies(Scope.BUILD, recurse=False):
            if elt in env:
                self.layout_add(elt.name, '/')
            elif elt.get_kind() == 'flatpak_image':
                self.layout_add(elt.name, staging_dir(elt))
                self.add_commands('export {}'.format(elt.name), [export_command(elt)])
            else:
                raise ElementError('Dependency {} is not of kind flatpak_image'.format(elt.name))

        super(FlatpakRepoElement, self).stage(sandbox)


# Plugin entry point
def setup():
    return FlatpakRepoElement

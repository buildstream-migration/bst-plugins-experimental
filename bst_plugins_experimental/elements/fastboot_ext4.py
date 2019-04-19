#  Copyright (C) 2018 Codethink Limited
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
#        Christopher Phang <christopher.phang@codethink.co.uk>

"""fastboot_ext4 image build element

A :mod:`ScriptElement <buildstream.scriptelement>` implementation for creating
fastboot ext4sparse images

The fastboot default configuration:
  .. literalinclude:: ../../../bst_external/elements/fastboot_ext4.yaml
     :language: yaml
"""

from buildstream import ScriptElement


# Element implementation for the 'FastbootExt4Image' kind.
# Based on the implementation for generating x86 images
class FastbootExt4ImageElement(ScriptElement):
    def configure(self, node):
        command_steps = [
            "create_dev_proc_shadow",
            "create_img",
            "install_img"
        ]

        self.node_validate(node,
            command_steps + ["base", "input"])

        for step in command_steps:
            if step not in node:
                raise ElementError("{}: Unexpectedly missing command step '{}'"
                                   .format(self, step))
            cmds = self.node_subst_list(node, step)
            self.add_commands(step, cmds)

        self.layout_add(self.node_subst_member(node, 'base'), "/")
        self.layout_add(None, '/buildstream')
        self.layout_add(self.node_subst_member(node, 'input'),
                        self.get_variable('build-root'))

        self.set_work_dir()
        self.set_install_root()
        self.set_root_read_only(True)


# Plugin entry point
def setup():
    return FastbootExt4ImageElement


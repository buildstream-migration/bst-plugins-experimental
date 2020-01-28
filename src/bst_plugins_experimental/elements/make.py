#
#  Copyright Bloomberg Finance LP
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
#        Ed Baunton <ebaunton1@bloomberg.net>

"""
make - Make build element
=========================
This is a `BuildElement
<https://docs.buildstream.build/master/buildstream.scriptelement.html#module-buildstream.scriptelement>`_
implementation for using GNU make based build.

.. note::

   The ``make`` element is available since `format version 9
   <https://docs.buildstream.build/master/format_project.html#project-format-version>`_

Here is the default configuration for the ``make`` element in full:

  .. literalinclude:: ../../../src/bst_plugins_experimental/elements/make.yaml
     :language: yaml

See `built-in functionality documentation
<https://docs.buildstream.build/master/buildstream.buildelement.html#core-buildelement-builtins>`_ for
details on common configuration options for build elements.
"""

from buildstream import BuildElement, SandboxFlags


# Element implementation for the 'make' kind.
class MakeElement(BuildElement):
    # Supports virtual directories (required for remote execution)
    BST_VIRTUAL_DIRECTORY = True

    # Enable command batching across prepare() and assemble()
    def configure_sandbox(self, sandbox):
        super().configure_sandbox(sandbox)
        self.batch_prepare_assemble(
            SandboxFlags.ROOT_READ_ONLY,
            collect=self.get_variable("install-root"),
        )


# Plugin entry point
def setup():
    return MakeElement

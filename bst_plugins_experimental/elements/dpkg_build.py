#  Copyright (C) 2017 Codethink Limited
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
#        Jonathan Maw <jonathan.maw@codethink.co.uk>
#        James Ennis <james.ennis@codethink.co.uk>

"""Dpkg build element

A :mod:`BuildElement <buildstream.buildelement>` implementation for using
dpkg elements

Default Configuration
~~~~~~~~~~~~~~~~~~~~~

The dpkg default configuration:
  .. literalinclude:: ../../../bst_external/elements/dpkg_build.yaml
     :language: yaml

Public data
~~~~~~~~~~~

This plugin writes to an element's public data.

split-rules
-----------

This plugin overwrites the element's split-rules with a list of its own
creation, creating a split domain for every package that it detected.
e.g.

.. code:: yaml

   public:
     bst:
       split-rules:
         foo:
         - /sbin/foo
         - /usr/bin/bar
         bar:
         - /etc/quux

dpkg-data
---------

control
'''''''

The control file will be written as raw text into the control field.
e.g.

.. code:: yaml

   public:
     bst:
       dpkg-data:
         foo:
           control: |
             Source: foo
             Section: blah
             Build-depends: bar (>= 1337), baz
             ...

name
''''

The name of the plugin will be written to the name field.
e.g.

.. code:: yaml

   public:
     bst:
       dpkg-data:
         bar:
           name: foobar

package-scripts
---------------

preinst, postinst, prerm and postrm scripts may be written to the
package if they are detected. They are written as raw text. e.g.

.. code:: yaml

   public:
     bst:
       package-scripts:
         foo:
           preinst: |
             #!/usr/bin/bash
             /sbin/ldconfig
         bar:
           postinst: |
             #!/usr/bin/bash
             /usr/share/fonts/generate_fonts.sh

"""

import filecmp
import os
import re

from buildstream import BuildElement, utils, ElementError


# Element implementation for the 'dpkg' kind.
class DpkgElement(BuildElement):
    def _get_packages(self, sandbox):
        controlfile = os.path.join("debian", "control")
        controlpath = os.path.join(
            sandbox.get_directory(),
            self.get_variable('build-root').lstrip(os.sep),
            controlfile
        )
        with open(controlpath) as f:
            return re.findall(r"Package:\s*(.+)\n", f.read())

    def configure(self, node):
        # __original_commands is needed for cache-key generation,
        # as commands can be altered during builds and invalidate the key
        super().configure(node)
        self.__original_commands = dict(self._BuildElement__commands)

    def get_unique_key(self):
        key = super().get_unique_key()
        # Overriding because we change self._BuildElement__commands mid-build, making it
        # unsuitable to be included in the cache key.
        for domain, cmds in self.__original_commands.items():
            key[domain] = cmds

        return key

    def assemble(self, sandbox):
        # Replace <PACKAGES> if no variable was set
        packages = self._get_packages(sandbox)
        self._BuildElement__commands = dict([
            (group, [
                c.replace("<PACKAGES>", " ".join(packages)) for c in commands
            ])
            for group, commands in self._BuildElement__commands.items()
        ])

        collectdir = super().assemble(sandbox)

        bad_overlaps = set()
        new_split_rules = {}
        new_dpkg_data = {}
        new_package_scripts = {}
        for package in packages:
            if not self._get_workspace():  # If we're not using a workspace
                package_path = os.path.join(sandbox.get_directory(),
                                            self.get_variable('build-root').lstrip(os.sep),
                                            'debian', package)
            else:  # We have a workspace open for this dpkg_build element
                workspace = self._get_workspace()
                package_path = os.path.join(workspace.get_absolute_path(),
                                            'debian', package)

            # Exclude DEBIAN files because they're pulled in as public metadata
            contents = ['/'+x for x in utils.list_relative_paths(package_path)
                        if x != "." and not x.startswith("DEBIAN")]
            new_split_rules[package] = contents

            # Check for any overlapping files that are different.
            # Since we're storing all these files together, we need to warn
            # because clobbering is bad!
            for content_file in contents:
                for split_package, split_contents in new_split_rules.items():
                    for split_file in split_contents:
                        content_file_path = os.path.join(package_path,
                                                         content_file.lstrip(os.sep))
                        split_file_path = os.path.join(os.path.dirname(package_path),
                                                       split_package,
                                                       split_file.lstrip(os.sep))
                        if (content_file == split_file and
                                os.path.isfile(content_file_path) and
                                not filecmp.cmp(content_file_path, split_file_path)):
                            bad_overlaps.add(content_file)

            # Store /DEBIAN metadata for each package.
            # DEBIAN/control goes into bst.dpkg-data.<package>.control
            controlpath = os.path.join(package_path, "DEBIAN", "control")
            if not os.path.exists(controlpath):
                raise ElementError("{}: package {} doesn't have a DEBIAN/control in {}!"
                                   .format(self.name, package, package_path))
            with open(controlpath, "r") as f:
                controldata = f.read()
            new_dpkg_data[package] = {"control": controldata, "name": package}

            # DEBIAN/{pre,post}{inst,rm} scripts go into bst.package-scripts.<package>.<script>
            scriptfiles = ["preinst", "postinst", "prerm", "postrm"]
            for s in scriptfiles:
                path = os.path.join(package_path, "DEBIAN", s)
                if os.path.exists(path):
                    if package not in new_package_scripts:
                        new_package_scripts[package] = {}
                    with open(path, "r") as f:
                        data = f.read()
                    new_package_scripts[package][s] = data

        bstdata = self.get_public_data("bst")
        bstdata["split-rules"] = new_split_rules
        bstdata["dpkg-data"] = new_dpkg_data
        if new_package_scripts:
            bstdata["package-scripts"] = new_package_scripts

        self.set_public_data("bst", bstdata)

        if bad_overlaps:
            self.warn('Destructive overlaps found in some files',
                      detail='\n'.join(bad_overlaps))

        return collectdir


# Plugin entry point
def setup():
    return DpkgElement

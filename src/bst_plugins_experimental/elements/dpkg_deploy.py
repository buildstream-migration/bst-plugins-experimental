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

"""Dpkg deployment element

A `ScriptElement
<https://docs.buildstream.build/master/buildstream.scriptelement.html#module-buildstream.scriptelement>`_
implementation for creating debian packages

Default Configuration
~~~~~~~~~~~~~~~~~~~~~

The dpkg_deploy default configuration:
  .. literalinclude:: ../../../src/bst_plugins_experimental/elements/dpkg_deploy.yaml
     :language: yaml

Public Data
~~~~~~~~~~~

This plugin uses the public data of the element indicated by `config.input`
to generate debian packages.

split-rules
-----------

This plugin consumes the input element's split-rules to identify which file
goes in which package, e.g.

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

The control field is used to generate the control file for each package, e.g.

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

If the "name" field is present, the generated package will use that field to
determine its name.
If "name" is not present, the generated package will be named
<element_name>-<package_name>

i.e. in an element named foo:

.. code:: yaml

   public:
     bst:
       dpkg-data:
         bar:
           name: foobar

will be named "foobar", while the following data:

.. code:: yaml

   public:
     bst:
       dpkg-data:
         bar:
           ...

will create a package named "foo-bar"

package-scripts
---------------

preinst, postinst, prerm and postrm scripts will be generated
based on data in pacakge-scripts, if it exists. The scripts are formatted as
raw text, e.g.

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

import hashlib
import os
import re
from buildstream import ScriptElement, Scope, utils, ElementError


def md5sum_file(path):
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# Element implementation for the 'dpkg_deploy' kind.
class DpkgDeployElement(ScriptElement):
    BST_REQUIRED_VERSION_MAJOR = 1
    BST_REQUIRED_VERSION_MINOR = 91

    def configure(self, node):
        node.validate_keys(["build-commands", "base", "input"])

        self.__input = self.node_subst_vars(node.get_scalar("input"))
        self.layout_add(self.node_subst_vars(node.get_scalar("base")), "/")
        self.layout_add(None, "/buildstream")
        self.layout_add(self.__input, self.get_variable("build-root"))
        self.unedited_cmds = {}
        if "build-commands" not in node:
            raise ElementError(
                "{}: Unexpectedly missing command: 'build-commands'".format(
                    self
                )
            )
        cmds = self.node_subst_sequence_vars(
            node.get_sequence("build-commands")
        )
        self.unedited_cmds["build-commands"] = cmds

        self.set_work_dir()
        self.set_install_root()
        self.set_root_read_only(True)

    def get_unique_key(self):
        key = super().get_unique_key()
        del key["commands"]
        key["unedited-commands"] = self.unedited_cmds
        return key

    def stage(self, sandbox):
        super().stage(sandbox)
        # For each package, create a subdir in build-root and copy the files to there
        # then reconstitute the /DEBIAN files.
        input_elm = self.search(Scope.BUILD, self.__input)
        if not input_elm:
            raise ElementError(
                "{}: Failed to find input element {} in build-depends".format(
                    self.name, self.__input
                )
            )

        bstdata = input_elm.get_public_data("bst")
        if "dpkg-data" not in bstdata:
            raise ElementError(
                "{}: input element {} does not have any bst.dpkg-data public data".format(
                    self.name, self.__input
                )
            )

        dpkg_data = bstdata.get_mapping("dpkg-data")
        for package, package_data in dpkg_data.items():
            package_name = package_data.get_str(
                "name", "{}-{}".format(input_elm.normal_name, package)
            )
            split_rules = bstdata.get_mapping("split-rules", {})

            if not ("split-rules" in bstdata and package in split_rules):
                raise ElementError(
                    "{}: Input element {} does not have bst.split-rules.{}".format(
                        self.name, self.__input.name, package
                    )
                )

            # FIXME: The package_splits variable is unused, which means the
            #        split rules from above are completely ignored, it appears
            #        that we are relying on Element.compute_manifest(), can
            #        we then remove this manual handling of split-rules ?
            #
            package_splits = split_rules.get_str_list(  # pylint: disable=unused-variable
                package
            )

            package_files = input_elm.compute_manifest(include=[package])
            src = os.path.join(
                sandbox.get_directory(),
                self.get_variable("build-root").lstrip(os.sep),
            )
            dst = os.path.join(src, package)
            os.makedirs(dst, exist_ok=True)

            # link only the files for this package into it's respective package directory
            def package_filter(filename, package_files=package_files):
                return filename in package_files

            utils.link_files(src, dst, filter_callback=package_filter)

            # Create this dir. If it already exists,
            # something unexpected has happened.
            debiandir = os.path.join(dst, "DEBIAN")
            os.makedirs(debiandir)

            # Recreate the DEBIAN files.
            # control is extracted verbatim, and is mandatory.
            if "control" not in package_data:
                raise ElementError(
                    "{}: Cannot reconstitute package {}".format(
                        self.name, package
                    ),
                    detail="There is no public.bst.dpkg-data.{}.control".format(
                        package
                    ),
                )
            controlpath = os.path.join(debiandir, "control")
            controltext = package_data.get_str("control")
            # Slightly ugly way of renaming the package
            controltext = re.sub(
                r"^Package:\s*\S+",
                "Package: {}".format(package_name),
                controltext,
            )
            with open(controlpath, "w") as f:
                f.write(controltext + "\n")

            # Generate a DEBIAN/md5sums file from the artifact
            md5sums = {}
            for split in package_files:
                filepath = os.path.join(src, split.lstrip(os.sep))
                if os.path.isfile(filepath):
                    md5sums[split] = md5sum_file(filepath)
            md5sumspath = os.path.join(debiandir, "md5sums")
            with open(md5sumspath, "w") as f:
                for path, md5sum in md5sums.items():
                    f.write("{}  {}\n".format(md5sum, path))

            # scripts may exist
            package_scripts = bstdata.get_mapping("package-scripts", {})
            if "package-scripts" in bstdata and package in package_scripts:
                for script in ["postinst", "preinst", "postrm", "prerm"]:
                    script_text = package_scripts.get_str(script, "")
                    if script_text:
                        filepath = os.path.join(debiandir, script)
                        with open(filepath, "w") as f:
                            f.write(script_text)
                        os.chmod(filepath, 0o755)

    def _packages_list(self):
        input_elm = self.search(Scope.BUILD, self.__input)
        if not input_elm:
            detail = "Available elements are {}".format(
                "\n".join([x.name for x in self.dependencies(Scope.BUILD)])
            )
            raise ElementError(
                "{} Failed to find element {}".format(self.name, self.__input),
                detail=detail,
            )

        bstdata = input_elm.get_public_data("bst")
        if "dpkg-data" not in bstdata:
            raise ElementError(
                "{}: Can't get package list for {}, no bst.dpkg-data".format(
                    self.name, self.__input
                )
            )

        dpkg_data = bstdata.get_mapping("dpkg-data", {})
        return " ".join(dpkg_data.keys())

    def _sub_packages_list(self, cmdlist):
        return [
            cmd.replace("<PACKAGES>", self._packages_list()) for cmd in cmdlist
        ]

    def assemble(self, sandbox):
        # Mangle commands here to replace <PACKAGES> with the list of packages.
        # It can't be done in configure (where it was originally set) because
        # we don't have access to the input element at that time.
        for group, commands in self.unedited_cmds.items():
            self.add_commands(group, self._sub_packages_list(commands))
        return super().assemble(sandbox)


# Plugin entry point
def setup():
    return DpkgDeployElement

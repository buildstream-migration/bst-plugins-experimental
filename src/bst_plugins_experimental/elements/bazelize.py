#
#  Copyright (C) 2020 Codethink Limited
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
#  License along with this library. If not, see <https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt>.
#
#  Authors:
#        Darius Makovsky <darius.makovsky@codethink.co.uk>
"""Bazelize kind Buildstream element plugin

It creates BUILD files calling bazel
[cc_* rules](https://docs.bazel.build/versions/master/be/c-cpp.html).

As an example considering an element `makelib.bst` producing an artifact
containing:
* usr/lib/lib.so
* usr/include/hdr.h

An element of this kind ('bazelize.bst') declaring a
`build-depends: makelib.bst` will produce a BUILD file containing:

.. code::

    package(default_visibility = ["//visibility:public"])
    load("@rules_cc//cc:defs.bzl", "cc_library")

    cc_library(
        name = "makelib",
        srcs = ['usr/lib/lib.so'],
        hdrs = ['usr/include/hdr.h']
    )
"""
import re
import os

from typing import (
    Generator,
    List,
    Set,
    Optional,
    Tuple,
    TYPE_CHECKING,
)
from buildstream import (  # pylint: disable=import-error
    Element,
    MappingNode,
    Node,
)

if TYPE_CHECKING:
    from buildstream.types import SourceRef  # pylint: disable=import-error
    from buildstream import Sandbox  # pylint: disable=import-error

# header regex
HDR_EXT = r"h(x{2}|p{2})?|h{2}|H|in(c|l)"
BAZELIZE_HDR_RE = re.compile(r"^.*\.(" + HDR_EXT + r")$")

# source regex
SRC_EXT = r"c(x{2}|p{2})|c{2}|c\+{2}|c|C|S|(pic\.)?(a|l?o)|so(\.\d+)*"
BAZELIZE_SOURCE_RE = re.compile(r"^.*\.(" + SRC_EXT + r")$")

# library regex
INTERFACE_EXT = r"ifso|tbd"
BAZELIZE_INTERFACE_RE = re.compile(r"^.*\.(" + INTERFACE_EXT + r")$")
SHARED_EXT = r"so|dll|dylib"
BAZELIZE_SHARED_RE = re.compile(r"^.*\.(" + SHARED_EXT + r")$")
STATIC_EXT = r"(pic\.)?a|lib"
BAZELIZE_STATIC_RE = re.compile(r"^.*\.(" + STATIC_EXT + r")$")


class BazelRuleEntry:  # pylint: disable=too-few-public-methods
    """Simple class to hold information about cc_* bazel rule targets and
    information relevant to harvesting this from the element"""

    # header regex
    HDR_RE = BAZELIZE_HDR_RE
    # source regex
    SOURCE_RE = BAZELIZE_SOURCE_RE
    INTERFACE_RE = BAZELIZE_INTERFACE_RE
    SHARED_RE = BAZELIZE_SHARED_RE
    STATIC_RE = BAZELIZE_STATIC_RE
    # the empty metarule
    NONE_RULE = "BST.BAZEL_NONE_RULE"
    # default rule
    DEFAULT_RULE = "cc_library"
    IMPORT_RULE = "cc_import"

    @staticmethod
    def get_directive(rules: Set[str]) -> str:
        """Formats a set of strings into a string expressing a bazel load
        directive from a standard rule definition and returns this string."""
        load_str = str()
        # discard the empty rule
        rules.discard(BazelRuleEntry.NONE_RULE)

        # return empty str if there are no rules
        if not rules:
            return load_str

        for rule in sorted(list(rules)):
            load_str += ', "{}"'.format(rule)
        return 'load("@rules_cc//cc:defs.bzl"{})'.format(load_str) + os.linesep

    def __init__(
        self,
        element: Element,
        manifest: Optional[Generator[str, None, None]] = None,
    ) -> None:
        self.name = element.normal_name
        self.bazel_rule: str = BazelRuleEntry.DEFAULT_RULE
        self._srcs: List[str] = []
        self._interface_lib: List[str] = []
        self._shared_lib: List[str] = []
        self._static_lib: List[str] = []
        self._hdrs: List[str] = []
        self.deps: List[str] = []
        self._copts: List[str] = []
        self._linkopts: List[str] = []

        bazelize_data = element.get_public_data("bazelize-data")
        if bazelize_data is not None:
            self.bazel_rule = bazelize_data.get_str("bazel-rule")
            self._copts = bazelize_data.get_str_list("copts")
            self._linkopts = bazelize_data.get_str_list("linkopts")

        # empty rules have no semantic meaning for the BUILD
        if self.bazel_rule == BazelRuleEntry.NONE_RULE:
            return

        # get target names of deps from element dependencies
        _deps = set()
        for dep in element.dependencies(recurse=False):
            _deps.add(dep.normal_name)
        self.deps = sorted(list(_deps))
        del _deps

        # sources and headers from manifest
        if manifest:
            self._match_manifest_items(manifest)
            # sort headers and sources
            self._srcs.sort()
            self._hdrs.sort()

        self.make_cc_import()

        return

    def make_cc_import(self) -> None:
        """Modifies the bazel rule to be a cc_import from cc_library if matching
        the criteria."""
        # don't modify rules that are not cc_library
        if self.bazel_rule != "cc_library":
            return

        # to be a valid cc_import:
        # 1. there must be 0 or 1 of interface, shared, and static library values
        critical_lengths = [
            (len(ls) <= 1)
            for ls in [self._interface_lib, self._shared_lib, self._static_lib]
        ]
        # 2. there must not be sources which do not overlap with shared or static values
        critical_lengths.append(
            len(
                set(self._srcs)
                - (set(self._shared_lib).union(set(self._static_lib)))
            )
            == 0
        )
        # 3. there must not be any copts,linkopts, or deps
        critical_lengths.extend(
            [(len(ls) == 0) for ls in [self._copts, self._linkopts, self.deps]]
        )

        if all(critical_lengths):
            self.bazel_rule = BazelRuleEntry.IMPORT_RULE

        return

    def _match_manifest_items(
        self, manifest: Generator[str, None, None]
    ) -> None:
        srcs = set()
        hdrs = set()
        interfaces = set()
        shareds = set()
        statics = set()

        for item in manifest:
            if re.match(BazelRuleEntry.SOURCE_RE, item):
                # looks like a source
                srcs.add(item)
                # regex overlap between SRC_RE and SHARED_RE/STATIC_RE
                if re.match(BazelRuleEntry.SHARED_RE, item):
                    shareds.add(item)
                elif re.match(BazelRuleEntry.STATIC_RE, item):
                    statics.add(item)
            elif re.match(BazelRuleEntry.HDR_RE, item):
                # looks like a header
                hdrs.add(item)
            elif re.match(BazelRuleEntry.INTERFACE_RE, item):
                # looks like an interface library
                interfaces.add(item)
            elif re.match(BazelRuleEntry.SHARED_RE, item):
                # looks like a shared library
                shareds.add(item)
            elif re.match(BazelRuleEntry.STATIC_RE, item):
                # looks like a static library
                statics.add(item)

        self._interface_lib += list(interfaces)
        self._shared_lib += list(shareds)
        self._static_lib += list(statics)
        self._srcs += list(srcs)
        self._hdrs += list(hdrs)

    def __eq__(self, other):
        # Target names cannot overlap so targets with the same names
        # should be considered to be equivalent.
        return other and self.name == other.name

    def __hash__(self):
        # This is defined by the implementation of __eq__()
        return hash(self.name)

    def __str__(self) -> str:
        """Implementation for representing the entry"""
        # avoid representing the empty targets
        if self.bazel_rule == BazelRuleEntry.NONE_RULE:
            return str()

        # workaround the regex overlap for library extensions
        if self.bazel_rule == BazelRuleEntry.IMPORT_RULE:
            self._srcs = []
        else:
            self._interface_lib = []
            self._shared_lib = []
            self._static_lib = []

        msg = (
            "{}(".format(self.bazel_rule)
            + os.linesep
            + '    name = "{}",'.format(self.name)
            + os.linesep
        )
        if self._srcs:
            msg += "    srcs = {},".format(self._srcs) + os.linesep
        if self._hdrs:
            msg += "    hdrs = {},".format(self._hdrs) + os.linesep
        if self._interface_lib:
            msg += (
                '    interface_library = "{}",'.format(self._interface_lib[0])
                + os.linesep
            )
        if self._shared_lib:
            msg += (
                '    shared_library = "{}",'.format(self._shared_lib[0])
                + os.linesep
            )
        if self._static_lib:
            msg += (
                '    static_library = "{}",'.format(self._static_lib[0])
                + os.linesep
            )
        if self.deps:
            msg += "    deps = {},".format(self.deps) + os.linesep
        if self._copts:
            msg += "    copts = {},".format(self._copts) + os.linesep
        if self._linkopts:
            msg += "    linkopts = {},".format(self._linkopts) + os.linesep
        msg += ")" + os.linesep
        return msg


class BazelizeElement(Element):
    """Buildstream element plugin kind formatting calls to cc_library rules"""

    # pylint: disable=attribute-defined-outside-init

    BST_MIN_VERSION = "2.0"
    BST_VIRTUAL_DIRECTORY = True

    def preflight(self) -> None:
        # the caller currently raises ElementError if runtime
        # dependencies are provided
        pass

    def stage(self, sandbox: "Sandbox") -> None:
        pass

    def configure_sandbox(self, sandbox: "Sandbox") -> None:
        pass

    def configure(self, node: MappingNode) -> None:
        node.validate_keys(
            ["buildfile-dir", "copts", "linkopts", "bazel-rule"]
        )

        # configure the path for the BUILD file and some options
        self.build_file_dir = node.get_str("buildfile-dir")
        self.copts = node.get_str_list("copts")
        self.linkopts = node.get_str_list("linkopts")
        self.bazel_rule = node.get_str("bazel-rule")

        # sort the options to gaurantee a deterministic key
        self.copts.sort()
        self.linkopts.sort()

    def get_unique_key(self) -> "SourceRef":
        return {
            "buildfile-dir": self.build_file_dir,
            "copts": self.copts,
            "linkopts": self.linkopts,
            "bazel-rule": self.bazel_rule,
        }

    @staticmethod
    def _gather_target(
        element: Element, manifest: Optional[Generator[str, None, None]] = None
    ) -> BazelRuleEntry:
        return BazelRuleEntry(element, manifest)

    def _gather_targets(self) -> Tuple[str, List[BazelRuleEntry]]:
        """Gather the required rules for the defined targets

        This returns a list of rule entry objects and a load directive str.
        """
        targets_set: Set[BazelRuleEntry] = set()

        for dep in self.dependencies(recurse=False):
            target = BazelizeElement._gather_target(
                dep, dep.compute_manifest()
            )
            # collect the target only if it's not an empty rule
            if target.bazel_rule != BazelRuleEntry.NONE_RULE:
                targets_set.add(target)

        # collect the element only if it's not an empty rule
        if self.bazel_rule != BazelRuleEntry.NONE_RULE:
            targets_set.add(BazelizeElement._gather_target(self))

        # sort by target name
        targets: List[BazelRuleEntry] = sorted(
            list(targets_set), key=lambda x: x.name
        )
        del targets_set

        # remove unbound dependencies and modify rules to be cc_imports if
        # necessary
        bound = {target.name for target in targets}
        for target in targets:
            target.deps = sorted(list(set(target.deps).intersection(bound)))
            target.make_cc_import()

        # get the load directive
        rule_types = {target.bazel_rule for target in targets}
        load_directive = BazelRuleEntry.get_directive(rule_types)

        return load_directive, targets

    def assemble(self, sandbox: "Sandbox") -> str:
        # format the visibility
        visibility = (
            'package(default_visibility = ["//visibility:{}"])'.format(
                "public"
            )
            + os.linesep
        )
        # gather the sorted list of targets and the load directive
        load_directive, targets = self._gather_targets()

        # attempt to write the BUILD file from assembled rule entries
        build_file_name = "BUILD"

        basedir = sandbox.get_virtual_directory()
        vdir = basedir.descend(
            *self.build_file_dir.lstrip(os.path.sep).split(os.path.sep),
            create=True
        )

        with vdir.open_file(build_file_name, mode="w") as f:
            # write the visibility
            f.write(visibility)
            # write the load directives
            f.write(load_directive)
            for target in targets:
                f.write(str(target))

        # Propagate the bazelize configuration data through public
        # data since we need to read it from reverse dependency
        # bazelize elements.
        #
        bazelize_data = Node.from_dict({})
        bazelize_data["copts"] = self.copts
        bazelize_data["linkopts"] = self.linkopts
        bazelize_data["bazel-rule"] = self.bazel_rule
        self.set_public_data("bazelize-data", bazelize_data)

        return os.path.sep


def setup():
    return BazelizeElement

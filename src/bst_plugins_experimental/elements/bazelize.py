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
"""Bazelise kind Buildstream element plugin

It creates BUILD files calling bazel
[cc_* rules](https://docs.bazel.build/versions/master/be/c-cpp.html).

As an example considering an element `makelib.bst` producing an artifact
containing:
    * usr/lib/lib.so
    * usr/include/hdr.h

An element of this kind ('bazelize.bst') declaring a
`build-depends: makelib.bst` will produce a BUILD file containing:

```
load("@rules_cc//cc:defs.bzl", "cc_library")

cc_library(
    name = "makelib",
    srcs = ['usr/lib/lib.so'],
    hdrs = ['usr/include/hdr.h']
)
```
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
    Scope,
    MappingNode,
)

if TYPE_CHECKING:
    from buildstream.types import SourceRef  # pylint: disable=import-error
    from buildstream import Sandbox  # pylint: disable=import-error

# header regex
HDR_EXT = r"h(x{2}|p{2})?|h{2}|H|in(c|l)"
BAZELIZE_HDR_RE = re.compile(r"^.*\.(" + HDR_EXT + r")$")

# source regex
SRC_EXT = r"c(x{2}|p{2})|c{2}|c\+{2}|C|S|(pic\.)?(a|l?o)|so(\.\d+)*"
BAZELIZE_SOURCE_RE = re.compile(r"^.*\.(" + SRC_EXT + r")$")


class BazelRuleEntry:  # pylint: disable=too-few-public-methods
    """Simple class to hold information about cc_* bazel rule targets and
    information relevant to harvesting this from the element"""

    # header regex
    HDR_RE = BAZELIZE_HDR_RE
    # source regex
    SOURCE_RE = BAZELIZE_SOURCE_RE
    # the empty metarule
    NONE_RULE = "BST.BAZEL_NONE_RULE"
    # default rule
    DEFAULT_RULE = "cc_library"

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
        self._hdrs: List[str] = []
        self._deps: List[str] = []
        self._copts: List[str] = []
        self._scope = Scope.RUN

        if element.get_kind() == "bazelize":
            self._scope = Scope.BUILD
            self.bazel_rule = element.bazel_rule
            self._copts = element.copts

        # empty rules have no semantic meaning for the BUILD
        if self.bazel_rule == BazelRuleEntry.NONE_RULE:
            return

        # sources and headers from manifest and element.sources
        _srcs = set()
        for source in element.sources():
            _srcs.add(os.path.basename(source.path))
        self._srcs = list(_srcs)
        del _srcs

        # get target names of deps from element dependencies
        _deps = set()
        for dep in element.dependencies(self._scope, recurse=False):
            _deps.add(dep.normal_name)
        self._deps = sorted(list(_deps))
        del _deps

        if manifest:
            self._match_manifest_items(manifest)

        # sort headers and sources
        self._srcs.sort()
        self._hdrs.sort()
        return

    def _match_manifest_items(
        self, manifest: Generator[str, None, None]
    ) -> None:
        srcs = set()
        hdrs = set()
        for item in manifest:
            _maybe = re.match(BazelRuleEntry.SOURCE_RE, item)
            if _maybe:
                # the item looks like a source
                srcs.add(item)
            else:
                _maybe = re.match(BazelRuleEntry.HDR_RE, item)
                if _maybe:
                    # the item looks like a header
                    hdrs.add(item)
        self._srcs += list(srcs)
        self._hdrs += list(hdrs)

    def __str__(self) -> str:
        """Implementation for representing the entry"""
        # avoid representing the empty targets
        if self.bazel_rule == BazelRuleEntry.NONE_RULE:
            return str()

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
        if self._deps:
            msg += "    deps = {},".format(self._deps) + os.linesep
        if self._copts:
            msg += "    copts = {},".format(self._copts) + os.linesep
        msg += ")" + os.linesep
        return msg


class BazelizeElement(Element):
    """Buildstream element plugin kind formatting calls to cc_library rules"""

    BST_MIN_VERSION = "2.0"
    # explicitly forbid run-time dependencies
    BST_FORBID_RDEPENDS = True
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
        # configure the path for the BUILD file and some options
        node.validate_keys(["buildfile-dir", "copts", "bazel-rule"])

        self.build_file_dir = self.node_subst_vars(  # pylint: disable=attribute-defined-outside-init
            node.get_scalar("buildfile-dir")
        )

        self.copts = self.node_subst_sequence_vars(  # pylint: disable=attribute-defined-outside-init
            node.get_sequence("copts")
        )
        # sort the options to gaurantee a unique key
        self.copts.sort()

        # get the rule for this element
        self.bazel_rule = self.node_subst_vars(  # pylint: disable=attribute-defined-outside-init
            node.get_scalar("bazel-rule")
        )

    def get_unique_key(self) -> "SourceRef":
        return {
            "buildfile-dir": self.build_file_dir,
            "copts": self.copts,
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

        for dep in self.dependencies(Scope.BUILD, recurse=False):
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

        rule_types = set()
        for target in targets:
            rule_types.add(target.bazel_rule)
        load_directive = BazelRuleEntry.get_directive(rule_types)

        return load_directive, targets

    def assemble(self, sandbox: "Sandbox") -> str:
        # gather the sorted list of targets and the load directive
        load_directive, targets = self._gather_targets()

        # attempt to write the BUILD file from assembled rule entries
        build_file_name = "BUILD." + self.normal_name

        basedir = sandbox.get_virtual_directory()
        vdir = basedir.descend(
            *self.build_file_dir.lstrip(os.path.sep).split(os.path.sep),
            create=True
        )

        with vdir.open_file(build_file_name, mode="w") as f:
            # write the load directives
            f.write(load_directive)
            for target in targets:
                f.write(str(target))
        return os.path.sep


def setup():
    return BazelizeElement

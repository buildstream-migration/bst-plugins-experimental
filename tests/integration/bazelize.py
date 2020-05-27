# Pylint doesn't play well with fixtures and dependency injection from pytest
# pylint: disable=redefined-outer-name

import os
import random
import pytest

from buildstream.testing.runcli import (  # pylint: disable=unused-import
    cli_integration as cli,
)
from buildstream.testing.integration import (  # pylint: disable=unused-import
    integration_cache,
)
from buildstream.testing.integration import assert_contains
from buildstream.testing._utils.site import HAVE_SANDBOX

pytestmark = pytest.mark.integration  # pylint: disable=invalid-name

DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "project")


def render_entry(entry):
    """Format a test entry as it is expected to appear in BUILD"""
    msg = ["{}(".format(entry["rule"]) + os.linesep]  # rule(
    msg += [
        '    name = "{}",'.format(entry["name"]) + os.linesep
    ]  #     name = "name",
    for item in ["srcs", "hdrs", "deps", "copts", "linkopts"]:
        if item in entry and entry[item]:
            msg += [
                "    {} = {},".format(item, entry[item]) + os.linesep
            ]  #     item = [values],
    msg += [")" + os.linesep]  # )
    return msg


@pytest.mark.datafiles(DATA_DIR)
@pytest.mark.skipif(
    not HAVE_SANDBOX, reason="Only available with a functioning sandbox"
)
# pylint: disable=too-many-locals
def test_gen_buildrules(cli, datafiles):
    project = str(datafiles)
    checkout = os.path.join(project, "checkout")
    prj_prefix = "bazelize-"
    element_name = "bazelize/empty.bst"
    build_file = "BUILD"  # default build file name

    # try to build
    result = cli.run(project=project, args=["build", element_name],)
    result.assert_success()

    # try to checkout
    result = cli.run(
        project=project,
        args=["artifact", "checkout", "--directory", checkout, element_name],
    )
    result.assert_success()

    # check for existence of the build file
    assert_contains(checkout, [os.path.sep + build_file])

    # format test content to check against the content of the build file
    # format expected library data
    prefix = "usr" + os.path.sep
    lib_prefix = prefix + "testlibs"
    hdr_prefix = prefix + "testincs"
    src_prefix = prefix + "testsrcs"

    def get_libs(libname):
        libs = [
            libname + lib
            for lib in [
                ".so",
                ".a",
                ".so.1234.4321",
                ".pic.a",
                ".pic.lo",
                ".lo",
            ]
        ]
        random.shuffle(libs)
        return [
            lib_prefix + os.path.sep + libname + os.path.sep + lib
            for lib in libs
        ]

    def get_srcs(libname):
        libs = [
            libname + lib
            for lib in [
                ".c",
                ".cc",
                ".cpp",
                ".cxx",
                ".c++",
                ".C",
                ".S",
                ".o",
                ".pic.o",
            ]
        ]
        random.shuffle(libs)
        return [
            src_prefix + os.path.sep + libname + os.path.sep + lib
            for lib in libs
        ]

    def get_hdrs(libname):
        hdrs = [
            libname + hdr
            for hdr in [".h", ".hh", ".hpp", ".hxx", ".inc", ".inl", ".H",]
        ]
        random.shuffle(hdrs)
        return [
            hdr_prefix + os.path.sep + libname + os.path.sep + hdr
            for hdr in hdrs
        ]

    def gen_cc_lib(num):
        libname = "cclib" + str(num)
        return {
            "rule": "cc_library",
            "name": prj_prefix + libname,
            "srcs": sorted(get_libs(libname) + get_srcs(libname)),
            "hdrs": sorted(get_hdrs(libname)),
            "deps": ["base"],
        }

    # format expected binary data
    # FIXME: bin1_srcs are [glob(app/*)] or ["app/afile.cpp", "app/bfile.c"]
    # see #6
    bin1_deps = [prj_prefix + "cclib2", prj_prefix + "cclib1"]
    bin1_opts = ["-I/lib/inc", "-I/include/someinc"]
    bin1_lopts = ["-lboost_thread", "-lboost_system"]
    bin1 = {
        "rule": "cc_binary",
        "name": prj_prefix + "bazelize",
        "deps": sorted(bin1_deps),
        "copts": sorted(bin1_opts),
        "linkopts": sorted(bin1_lopts),
    }

    # nb. current rules are sorted by name field in the plugin
    expected = [
        'package(default_visibility = ["//visibility:public"])' + os.linesep
    ]
    expected.extend(
        [
            'load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library")'
            + os.linesep
        ]
    )
    expected += render_entry(bin1)
    expected += render_entry(gen_cc_lib(1))
    expected += render_entry(gen_cc_lib(2))

    with open(os.path.join(checkout, build_file), "r") as fdata:
        artifact = fdata.readlines()

    assert artifact == expected

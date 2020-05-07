# Pylint doesn't play well with fixtures and dependency injection from pytest
# pylint: disable=redefined-outer-name
#
#  Copyright (C) 2018-2020 Codethink Limited
#  Copyright (C) 2018 Bloomberg Finance LP
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
#  Authors: Tristan Van Berkom <tristan.vanberkom@codethink.co.uk>
#           Jonathan Maw <jonathan.maw@codethink.co.uk>
#           William Salmon <will.salmon@codethink.co.uk>
#

import os

import pytest

from buildstream.exceptions import ErrorDomain
from buildstream import _yaml

from buildstream.testing import cli  # pylint: disable=unused-import
from buildstream.testing._utils.site import HAVE_GIT

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "git_tag",
)


## This test needs internet access which is not the best
## Something like https://github.com/git-lfs/lfs-test-server
## should allow for off line test but seems to need a very new
## version of git-lfs
@pytest.mark.skipif(HAVE_GIT is False, reason="git is not available")
@pytest.mark.datafiles(os.path.join(DATA_DIR, "lfs"))
def test_gitlfs(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkoutdir = os.path.join(str(tmpdir), "checkout")

    element = {
        "kind": "import",
        "sources": [
            {
                "kind": "git_tag",
                "url": "https://gitlab.com/buildstream/testing/test-lfs-repo",
                "track": "master",
                "ref": "85b163a6252154d93c3f3320e95866b598c07835",
                "use-lfs": True,
            }
        ],
    }
    _yaml.roundtrip_dump(element, os.path.join(project, "target.bst"))

    result = cli.run(project=project, args=["source", "fetch", "target.bst"])
    result.assert_success()
    result = cli.run(project=project, args=["build", "target.bst"])
    result.assert_success()

    result = cli.run(
        project=project,
        args=[
            "artifact",
            "checkout",
            "target.bst",
            "--directory",
            checkoutdir,
        ],
    )
    result.assert_success()
    with open(os.path.join(checkoutdir, str("cat.bin")), "br") as fl:
        count = len(fl.read())
        print(count)
        assert count > 10 ** 5
        assert (
            "oid sha256:cacc5757993c49e811bef86a7075581e4737226313a41aed524e89739ea82bfb"
            not in str(fl.read())
        )


## This test needs internet access which is not the best
## Something like https://github.com/git-lfs/lfs-test-server
## should allow for off line test but seems to need a very new
## version of git-lfs
@pytest.mark.skipif(HAVE_GIT is False, reason="git is not available")
@pytest.mark.datafiles(os.path.join(DATA_DIR, "lfs"))
@pytest.mark.parametrize(
    "Explicit", [True, False],
)
def test_gitlfs_off(cli, tmpdir, datafiles, Explicit):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkoutdir = os.path.join(str(tmpdir), "checkout")

    element = {
        "kind": "import",
        "sources": [
            {
                "kind": "git_tag",
                "url": "https://gitlab.com/buildstream/testing/test-lfs-repo",
                "track": "master",
                "ref": "85b163a6252154d93c3f3320e95866b598c07835",
            }
        ],
    }
    if Explicit:
        element["sources"][0]["use-lfs"] = False
    _yaml.roundtrip_dump(element, os.path.join(project, "target.bst"))

    result = cli.run(project=project, args=["source", "fetch", "target.bst"])
    result.assert_success()
    result = cli.run(project=project, args=["build", "target.bst"])
    result.assert_success()

    result = cli.run(
        project=project,
        args=[
            "artifact",
            "checkout",
            "target.bst",
            "--directory",
            checkoutdir,
        ],
    )
    result.assert_success()
    with open(os.path.join(checkoutdir, str("cat.bin")), "r") as fl:
        assert (
            "oid sha256:cacc5757993c49e811bef86a7075581e4737226313a41aed524e89739ea82bfb"
            in fl.read()
        )


## This test needs internet access which is not the best
## Something like https://github.com/git-lfs/lfs-test-server
## should allow for off line test but seems to need a very new
## version of git-lfs
@pytest.mark.skipif(HAVE_GIT is False, reason="git is not available")
@pytest.mark.datafiles(os.path.join(DATA_DIR, "lfs"))
def test_gitlfs_notset(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)

    element = {
        "kind": "import",
        "sources": [
            {
                "kind": "git_tag",
                "url": "https://gitlab.com/buildstream/testing/test-lfs-repo",
                "track": "master",
                "ref": "85b163a6252154d93c3f3320e95866b598c07835",
            }
        ],
    }
    _yaml.roundtrip_dump(element, os.path.join(project, "target.bst"))

    with open(os.path.join(project, "project.conf"), "a+") as fl:
        fl.write(
            """fatal-warnings:
  - git_tag:unused-lfs
"""
        )

    result = cli.run(project=project, args=["source", "fetch", "target.bst"])
    result.assert_main_error(ErrorDomain.STREAM, None)
    result.assert_task_error(ErrorDomain.PLUGIN, "git_tag:unused-lfs")

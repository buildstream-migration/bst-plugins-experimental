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
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Thomas Coldrick <thomas.coldrick@codethink.co.uk>
#

# Pylint doesn't play well with fixtures and dependency injection from pytest
# pylint: disable=redefined-outer-name

import os
import pytest

from buildstream.exceptions import ErrorDomain
from buildstream.testing import cli  # pylint: disable=unused-import

DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "bazel",)


@pytest.mark.datafiles(DATA_DIR)
def test_basic(cli, datafiles):
    project = str(datafiles)
    element_name = "basic.bst"

    result = cli.run(project=project, args=["source", "fetch", element_name])
    assert result.exit_code == 0

    assert cli.get_element_state(project, element_name) == "buildable"


@pytest.mark.datafiles(DATA_DIR)
def test_multi_url(cli, datafiles):
    project = str(datafiles)
    element_name = "multi-url.bst"

    result = cli.run(project=project, args=["source", "fetch", element_name])
    assert result.exit_code == 0

    assert cli.get_element_state(project, element_name) == "buildable"


@pytest.mark.datafiles(DATA_DIR)
def test_no_sha(cli, datafiles):
    project = str(datafiles)
    element_name = "no-sha.bst"

    result = cli.run(project=project, args=["source", "fetch", element_name])
    result.assert_main_error(ErrorDomain.STREAM, None)
    result.assert_task_error(ErrorDomain.PLUGIN, "bazel_source:missing-sha256")

    assert cli.get_element_state(project, element_name) == "buildable"

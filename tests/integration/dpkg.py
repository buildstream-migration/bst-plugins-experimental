# Pylint doesn't play well with fixtures and dependency injection from pytest
# pylint: disable=redefined-outer-name

import os
import pytest

from buildstream.testing.runcli import (  # pylint: disable=unused-import
    cli_integration as cli,
)
from buildstream.testing.integration import (  # pylint: disable=unused-import
    integration_cache,
)
from buildstream.testing.integration import assert_contains
from buildstream.testing._utils.site import HAVE_SANDBOX

pytestmark = pytest.mark.integration


DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "project")


@pytest.mark.datafiles(DATA_DIR)
@pytest.mark.skipif(
    not HAVE_SANDBOX, reason="Only available with a functioning sandbox"
)
def test_dpkg_build(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, "checkout")

    result = cli.run(project=project, args=["build", "dpkg-build-test.bst"])
    result.assert_success()

    result = cli.run(
        project=project,
        args=[
            "artifact",
            "checkout",
            "--directory",
            checkout_dir,
            "dpkg-build-test.bst",
        ],
    )
    result.assert_success()

    assert_contains(
        checkout_dir, ["/usr/share/foo", "/usr/share/doc/test/changelog.gz"]
    )


@pytest.mark.datafiles(DATA_DIR)
@pytest.mark.skipif(
    not HAVE_SANDBOX, reason="Only available with a functioning sandbox"
)
def test_dpkg_deploy(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, "debian_package")

    result = cli.run(project=project, args=["build", "dpkg-deploy-test.bst"])
    result.assert_success()

    result = cli.run(
        project=project,
        args=[
            "artifact",
            "checkout",
            "--directory",
            checkout_dir,
            "dpkg-deploy-test.bst",
        ],
    )
    result.assert_success()

    # FIXME: assert_contains() doesn't seem to like this .deb file
    assert os.listdir(checkout_dir) == ["test_0.1_amd64.deb"]

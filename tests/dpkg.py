import os
import pytest

from tests.testutils import cli_integration as cli
from tests.testutils.integration import assert_contains

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_dpkg_build(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'checkout')

    result = cli.run(project=project, args=['build', 'dpkg-build-test.bst'])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', 'dpkg-build-test.bst', checkout_dir])
    result.assert_success()

    assert_contains(checkout_dir, ['/usr/share/foo', '/usr/share/doc/test/changelog.gz'])


@pytest.mark.datafiles(DATA_DIR)
def test_dpkg_deploy(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'debian_package')

    result = cli.run(project=project, args=['build', 'dpkg-deploy-test.bst'])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', 'dpkg-deploy-test.bst', checkout_dir])
    result.assert_success()

    # FIXME: assert_contains() doesn't seem to like this .deb file
    assert os.listdir(checkout_dir) == ['test_0.1_amd64.deb']

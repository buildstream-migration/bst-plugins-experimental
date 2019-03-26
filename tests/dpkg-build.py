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
    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkout_dir = os.path.join(cli.directory, 'checkout')

    result = cli.run(project=project, args=['build', 'dpkg-build-test.bst'])
    assert result.exit_code == 0

    result = cli.run(project=project, args=['checkout', 'dpkg-build-test.bst', checkout_dir])
    assert result.exit_code == 0

    assert_contains(checkout_dir, ['/usr/share/foo', '/usr/share/doc/test/changelog.gz'])

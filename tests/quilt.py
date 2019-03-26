import os
import pytest

from tests.testutils import cli_integration as cli
from tests.testutils.integration import assert_contains

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_quilt_build(cli, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkout = os.path.join(cli.directory, 'quilt_checkout')

    result = cli.run(project=project, args=['build', "quilt-build-test.bst"])
    assert result.exit_code == 0

    result = cli.run(project=project, args=['checkout', "quilt-build-test.bst", checkout])
    assert result.exit_code == 0

    assert_contains(checkout, ['/patches/series','/patches/test','/src/hello.c'])

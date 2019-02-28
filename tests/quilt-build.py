import os
import pytest

from tests.testutils import cli_integration as cli
from tests.testutils import plugin_import
from tests.testutils.integration import assert_contains

#pytestmark = pytest.mark.integration

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_quilt_build(cli, datafiles, plugin_import):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkout = os.path.join(cli.directory, 'checkout')
    element_name = 'quilt-build/quilt-build-test.bst'

    result = cli.run(project=project, args=['build', element_name])
    assert result.exit_code == 0

    result = cli.run(project=project, args=['artifact', 'checkout', element_name, '--directory', checkout])
    assert result.exit_code == 0

    assert_contains(checkout, ['/patches/series','/patches/test','/src/hello.c'])

import os
import pytest

from tests.testutils import cli_integration, cli
from tests.testutils.integration import assert_contains


DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.integration
@pytest.mark.datafiles(DATA_DIR)
def test_docker_source_build(cli_integration, datafiles):

    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkout = os.path.join(cli_integration.directory, 'checkout')
    element_name = 'docker-source/docker-source-test.bst'

    result = cli_integration.run(project=project, args=['build', element_name])
    assert result.exit_code == 0

    result = cli_integration.run(project=project, args=['checkout', element_name, checkout])
    assert result.exit_code == 0

    assert_contains(checkout, ['/etc/os-release'])

import os
import pytest

from tests.testutils import cli
from tests.testutils.integration import assert_contains

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_docker_fetch(cli, datafiles):
    project = str(datafiles)
    result = cli.run(project=project, args=['fetch', 'dockerhub-alpine.bst'])
    result.assert_success()

@pytest.mark.datafiles(DATA_DIR)
def test_docker_source_build(cli, datafiles):
    project = str(datafiles)
    checkout = os.path.join(cli.directory, 'checkout')

    result = cli.run(project=project, args=['build', 'docker-source-test.bst'])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', 'docker-source-test.bst', checkout])
    result.assert_success()

    assert_contains(checkout, ['/etc/os-release'])

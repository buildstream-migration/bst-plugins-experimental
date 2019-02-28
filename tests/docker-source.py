import os
import pytest

from buildstream.plugintestutils import cli
from buildstream.plugintestutils.integration import assert_contains

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_docker_fetch(cli, datafiles):

    project = os.path.join(datafiles.dirname, datafiles.basename)
    docker_alpine_base = 'docker-source/dependencies/dockerhub-alpine.bst'

    result = cli.run(project=project, args=['source', 'fetch', docker_alpine_base])
    result.assert_success()

@pytest.mark.integration
@pytest.mark.datafiles(DATA_DIR)
def test_docker_source_build(cli, datafiles):

    project = os.path.join(datafiles.dirname, datafiles.basename)
    checkout = os.path.join(cli.directory, 'checkout')
    element_name = 'docker-source/docker-source-test.bst'

    result = cli.run(project=project, args=['build', element_name])
    result.assert_success()

    result = cli.run(project=project, args=['artifact', 'checkout', element_name, '--directory', checkout])
    result.assert_success()

    assert_contains(checkout, ['/etc/os-release'])

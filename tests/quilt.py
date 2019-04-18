import os
import pytest

from buildstream.testing import cli_integration as cli
from buildstream.testing.integration import assert_contains

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_quilt_build(cli, datafiles):
    project = str(datafiles)
    checkout = os.path.join(cli.directory, 'quilt_checkout')

    result = cli.run(project=project, args=['build', "quilt-build-test.bst"])
    result.assert_success()

    result = cli.run(project=project, args=[
        'artifact', 'checkout', '--directory', checkout, 'quilt-build-test.bst'
    ])
    result.assert_success()

    assert_contains(checkout, ['/patches/series','/patches/test','/src/hello.c'])

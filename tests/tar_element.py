import os
import pytest
import tarfile

from tests.testutils import cli_integration as cli
from tests.testutils.integration import assert_contains

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_tar_build(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'tar_checkout')
    tarpath = os.path.join(checkout_dir, 'hello.tar.gz')

    result = cli.run(project=project, args=['build', 'tar-test.bst'])
    result.assert_success()

    result = cli.run(project=project, args=['checkout', 'tar-test.bst',
        checkout_dir])
    result.assert_success()

    assert_contains(checkout_dir, ["/hello.tar.gz"])

    tar_hello = tarfile.open(tarpath)
    contents = tar_hello.getnames()
    assert contents == ['hello.c']

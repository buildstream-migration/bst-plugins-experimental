# Pylint doesn't play well with fixtures and dependency injection from pytest
# pylint: disable=redefined-outer-name

import hashlib
import os
import tarfile

import pytest

from buildstream.testing.integration import assert_contains
from buildstream.testing.integration import integration_cache  # pylint: disable=unused-import
from buildstream.testing.runcli import cli_integration as cli  # pylint: disable=unused-import

pytestmark = pytest.mark.integration

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)


BLOCKSIZE = 65536


@pytest.mark.datafiles(DATA_DIR)
def test_tar_build(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'tar_checkout')
    tarpath = os.path.join(checkout_dir, 'hello.tar.gz')
    element_name = 'tar/tar-test.bst'

    result = cli.run(project=project, args=['build', element_name])
    result.assert_success()

    result = cli.run(project=project, args=['artifact', 'checkout', '--directory', checkout_dir, element_name])
    result.assert_success()

    assert_contains(checkout_dir, ["/hello.tar.gz"])

    tar_hello = tarfile.open(tarpath)
    contents = tar_hello.getnames()
    assert contents == ['hello.c']


@pytest.mark.datafiles(DATA_DIR)
def test_tar_checksums(cli, datafiles):
    project = str(datafiles)
    checkout_dir = os.path.join(cli.directory, 'tar_checkout')
    element_name = 'tar/tar-test-checksums.bst'

    result = cli.run(project=project, args=['build', element_name])
    result.assert_success()

    result = cli.run(project=project, args=['artifact', 'checkout', '--directory', checkout_dir, element_name])
    result.assert_success()

    assert_contains(checkout_dir, ["/hello.tar.gz", "/hello.sha256sum", "/hello.md5sum"])

    with open(os.path.join(checkout_dir, "hello.sha256sum"), 'r') as f:
        file_sha256 = f.read().strip()
    with open(os.path.join(checkout_dir, "hello.md5sum"), 'r') as f:
        file_md5 = f.read().strip()
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()

    with open(os.path.join(checkout_dir, "hello.tar.gz"), 'rb') as tar:
        while True:
            buf = tar.read(BLOCKSIZE)
            if not buf:
                break
            sha256.update(buf)
            md5.update(buf)

    actual_sha256 = sha256.hexdigest()
    actual_md5 = md5.hexdigest()
    assert file_sha256 == actual_sha256
    assert file_md5 == actual_md5

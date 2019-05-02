import os
import pytest

from tests.testutils import cli_integration as cli
from tests.testutils.vm_test_utils import vm_test
from tests.testutils.integration import assert_contains

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "project"
)

@pytest.mark.datafiles(DATA_DIR)
def test_x86image_run(cli, datafiles):
    project = str(datafiles)
    checkout = os.path.join(cli.directory, 'x86image_checkout')
    img_path = os.path.join(checkout, 'sda.img')

    result = cli.run(project=project, args=['build', "x86image.bst"])
    result.assert_success()

    # Pass `--hardlinks` to reduce I/O
    result = cli.run(project=project, args=['checkout', '--hardlinks', "x86image.bst", checkout])
    result.assert_success()

    assert_contains(checkout, ['/sda.img'])

    result = vm_test(img_path, dialog='minimal')
    assert result == 0

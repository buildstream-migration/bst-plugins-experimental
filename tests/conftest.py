import pytest

from buildstream.testing import sourcetests_collection_hook, register_repo_kind
from tests.sources.ostreerepo import OSTree
from tests.sources.gitrepo import Git


#################################################
#            Implement pytest option            #
#################################################
def pytest_addoption(parser):
    parser.addoption('--integration', action='store_true', default=False,
                     help='Run integration tests')


def pytest_runtest_setup(item):
    # Without --integration: skip tests not marked with 'integration'
    if not item.config.getvalue('integration'):
        if item.get_closest_marker('integration'):
            pytest.skip('skipping integration test')


# TODO: can we get this from somewhere? pkg_resources?
package_name = "bst_plugins_experimental"


# Register a repo type to run the ostree plugin through buildstream's
# generic source plugin tests
register_repo_kind('ostree', OSTree, package_name)
register_repo_kind('git_tag', Git, package_name)


# This hook enables pytest to collect the templated source tests from
# buildstream.testing
def pytest_sessionstart(session):
    sourcetests_collection_hook(session)

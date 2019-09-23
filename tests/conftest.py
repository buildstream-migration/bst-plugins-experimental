import pytest

from buildstream.testing import sourcetests_collection_hook
from bst_plugins_experimental.testutils import register_sources


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


register_sources()


# This hook enables pytest to collect the templated source tests from
# buildstream.testing
def pytest_sessionstart(session):
    sourcetests_collection_hook(session)

from buildstream.testing import register_repo_kind
from .ostreerepo import OSTree

def register_sources():
    package_name = 'bst_plugins_experimental'
    register_repo_kind('ostree', OSTree, package_name)

from buildstream.testing import register_repo_kind

from .repo import Git, OSTree, Tar


# TODO: can we get this from somewhere? pkg_resources?
package_name = "bst_plugins_experimental"


def register_sources():
    register_repo_kind("ostree", OSTree, package_name)
    register_repo_kind("git_tag", Git, package_name)
    register_repo_kind("tar", Tar, package_name)

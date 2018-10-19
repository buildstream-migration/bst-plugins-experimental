import tarfile
import os

from buildstream import Element, Scope

class TarElement(Element):

    # The tarball's output is its dependencies, so
    # we must rebuild if they change
    BST_STRICT_REBUILD = True

    # Tarballs don't need runtime dependencies
    BST_FORBID_RDEPENDS = True

    # Our only sources are previous elements, so we forbid
    # remote sources
    BST_FORBID_SOURCES = True

    def configure(self, node):
        self.node_validate(node, [])

    def preflight(self):
        pass

    def get_unique_key(self):
        return 1

    def configure_sandbox(self, sandbox):
        pass

    def stage(self, sandbox):
        pass

    def assemble(self, sandbox):
        basedir = sandbox.get_directory()
        inputdir = os.path.join(basedir, 'input')
        outputdir = os.path.join(basedir, 'output')
        os.makedirs(inputdir, exist_ok=True)
        os.makedirs(outputdir, exist_ok=True)

        tarname = os.path.join(outputdir, 'files.tar')

        # Stage deps in the sandbox root
        with self.timed_activity("Staging dependencies", silent_nested=True):
            self.stage_dependency_artifacts(sandbox, Scope.BUILD, path='/input')

        with self.timed_activity("Creating tarball", silent_nested=True):
            with tarfile.TarFile(name=tarname, mode='w') as tar:
                for f in os.listdir(inputdir):
                    tar.add(os.path.join(inputdir, f), arcname=f)

        return '/output'

def setup():
    return TarElement

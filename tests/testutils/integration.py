import os

from buildstream import _yaml


# Return a list of files relative to the given directory
def walk_dir(root):
    for dirname, dirnames, filenames in os.walk(root):
        # print path to all subdirectories first.
        for subdirname in dirnames:
            yield os.path.join(dirname, subdirname)[len(root):]

        # print path to all filenames.
        for filename in filenames:
            yield os.path.join(dirname, filename)[len(root):]

#!/usr/bin/env python3
#
#  Copyright (C) 2017 Codethink Limited
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Tristan Maat <tristan.maat@codethink.co.uk>
#        James Ennis  <james.ennis@codethink.co.uk>

import os
import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    print("BuildStream requires setuptools in order to locate plugins. Install "
          "it using your package manager (usually python3-setuptools) or via "
          "pip (pip3 install setuptools).")
    sys.exit(1)

###############################################################################
#                          Gather Requirements                                #
###############################################################################

def parse_requirements(requirements_file):
    with open(requirements_file, 'r') as f:
        reqs = [line.strip() for line in f.readlines()
                if not line.strip().startswith('#') and line != '']
    return reqs

install_requires = parse_requirements('requirements/install-requirements.txt')


###############################################################################
#                             Parse README                                    #
###############################################################################
with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                       'README.rst')) as readme:
    long_description = readme.read()


setup(name='bst-plugins-experimental',
      version="1.93.1",
      description="A collection of experimental BuildStream plugins.",
      long_description=long_description,
      long_description_content_type='text/x-rst; charset=UTF-8',
      license='LGPL',
      url='https://gitlab.com/BuildStream/bst-plugins-experimental',
      project_urls={
          'Documentation': 'https://buildstream.gitlab.io/bst-plugins-experimental/',
      },
      package_dir={'': 'src'},
      packages=find_packages(where='src'),
      include_package_data=True,
      install_requires=install_requires,
      entry_points={
          'buildstream.plugins.elements': [
              'bazel_build = bst_plugins_experimental.elements.bazel_build',
              'cmake = bst_plugins_experimental.elements.cmake',
              'dpkg_build = bst_plugins_experimental.elements.dpkg_build',
              'dpkg_deploy = bst_plugins_experimental.elements.dpkg_deploy',
              'flatpak_image = bst_plugins_experimental.elements.flatpak_image',
              'flatpak_repo = bst_plugins_experimental.elements.flatpak_repo',
              'x86image = bst_plugins_experimental.elements.x86image',
              'fastbootBootImage = bst_plugins_experimental.elements.fastboot_bootimg',
              'fastbootExt4Image = bst_plugins_experimental.elements.fastboot_ext4',
              'collect_integration = bst_plugins_experimental.elements.collect_integration',
              'collect_manifest = bst_plugins_experimental.elements.collect_manifest',
              'meson = bst_plugins_experimental.elements.meson',
              'make = bst_plugins_experimental.elements.make',
              'oci = bst_plugins_experimental.elements.oci',
              'tar_element = bst_plugins_experimental.elements.tar_element',
              'makemaker = bst_plugins_experimental.elements.makemaker',
              'modulebuild = bst_plugins_experimental.elements.modulebuild',
              'qmake = bst_plugins_experimental.elements.qmake',
              'distutils = bst_plugins_experimental.elements.distutils',
              'pip = bst_plugins_experimental.elements.pip'
          ],
          'buildstream.plugins.sources': [
              'bazel_source = bst_plugins_experimental.sources.bazel_source',
              'deb = bst_plugins_experimental.sources.deb',
              'git_tag = bst_plugins_experimental.sources.git_tag',
              'pip = bst_plugins_experimental.sources.pip',
              'quilt = bst_plugins_experimental.sources.quilt',
              'ostree = bst_plugins_experimental.sources.ostree',
              'cargo = bst_plugins_experimental.sources.cargo',
              'tar = bst_plugins_experimental.sources.tar',
          ],
          'buildstream.tests.source_plugins': [
              'bst_plugins_experimental = bst_plugins_experimental.testutils',
          ]
      },
      extras_require={
          'ostree': ["PyGObject"],
          'cargo': ["pytoml"],
          'bazel': ["requests"],
          'deb': ["arpy"],
      },
      zip_safe=False)
# eof setup()

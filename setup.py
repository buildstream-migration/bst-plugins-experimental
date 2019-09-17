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
plugin_requires = parse_requirements('requirements/plugin-requirements.txt')
test_requires = parse_requirements('requirements/test-requirements.txt')

setup(name='bst-plugins-experimental',
      version="0.12.0",
      description="A collection of experimental BuildStream plugins.",
      license='LGPL',
      package_dir={'': 'src'},
      packages=find_packages(where='src'),
      include_package_data=True,
      install_requires=install_requires,
      package_data={
          'buildstream': [
              'src/bst_plugins_experimental/elements/**.yaml'
          ]
      },
      entry_points={
          'buildstream.plugins': [
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
              'tar_element = bst_plugins_experimental.elements.tar_element',
              'makemaker = bst_plugins_experimental.elements.makemaker',
              'modulebuild = bst_plugins_experimental.elements.modulebuild',
              'qmake = bst_plugins_experimental.elements.qmake',
              'distutils = bst_plugins_experimental.elements.distutils',
              'git_tag = bst_plugins_experimental.sources.git_tag',
              'quilt = bst_plugins_experimental.sources.quilt',
              'ostree = bst_plugins_experimental.sources.ostree',
              'oci = bst_plugins_experimental.elements.oci'
              'cargo = bst_plugins_experimental.sources.cargo',
          ]
      },
      tests_require=test_requires + plugin_requires,
      extras_require={
          'ostree': ["PyGObject"],
          'cargo': ["pytoml"],
      },
      zip_safe=False)
# eof setup()

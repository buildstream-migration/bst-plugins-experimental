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

with open('plugin-requirements.txt', 'r') as plugin_req_file:
    plugin_requires = [line for line in plugin_req_file.readlines()
            if not line.strip().startswith('#') and line != '']

setup(name='bst-plugins-experimental',
      version="0.12.0",
      description="A collection of experimental BuildStream plugins.",
      license='LGPL',
      packages=find_packages(exclude=['tests', 'tests.*']),
      include_package_data=True,
      install_requires=['setuptools'],
      package_data={
          'buildstream': [
              'bst_plugins_experimental/elements/**.yaml'
          ]
      },
      entry_points={
          'buildstream.plugins': [
              'cmake = bst_plugins_experimental.elements.cmake',
              'docker = bst_plugins_experimental.sources.docker',
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
              'git_tag = bst_plugins_experimental.sources.git_tag',
              'quilt = bst_plugins_experimental.sources.quilt',
              'ostree = bst_plugins_experimental.sources.ostree'
          ]
      },
      setup_requires=['pytest-runner', 'setuptools_scm'],
      tests_require=['pep8',
                     # Pin coverage to 4.2 for now, we're experiencing
                     # random crashes with 4.4.2
                     'coverage == 4.4.0',
                     'pytest-datafiles',
                     'pytest-env',
                     'pytest-pep8',
                     'pytest-cov',
                     # Provide option to run tests in parallel, less reliable
                     'pytest-xdist',
                     'pytest >= 3.1.0']
                     + plugin_requires,
      zip_safe=False
)  #eof setup()

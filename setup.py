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

setup(name='BuildStream-external',
      version="0.15.0",
      description="A collection of BuildStream plugins that don't fit in with the core plugins for whatever reason.",
      license='LGPL',
      packages=find_packages(exclude=['tests', 'tests.*']),
      include_package_data=True,
      install_requires=[
          'requests',
          'setuptools'
      ],
      package_data={
          'buildstream': [
              'bst_external/elements/**.yaml'
          ]
      },
      entry_points={
          'buildstream.plugins': [
              'docker = bst_external.sources.docker',
              'dpkg_build = bst_external.elements.dpkg_build',
              'dpkg_deploy = bst_external.elements.dpkg_deploy',
              'flatpak_image = bst_external.elements.flatpak_image',
              'flatpak_repo = bst_external.elements.flatpak_repo',
              'x86image = bst_external.elements.x86image',
              'fastbootBootImage = bst_external.elements.fastboot_bootimg',
              'fastbootExt4Image = bst_external.elements.fastboot_ext4',
              'collect_integration = bst_external.elements.collect_integration',
              'collect_manifest = bst_external.elements.collect_manifest',
              'git_tag = bst_external.sources.git_tag',
              'quilt = bst_external.sources.quilt',
              'tar_element = bst_external.elements.tar_element',
              'oci = bst_external.elements.oci'
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
                     'pytest >= 3.1.0'],
      zip_safe=False
)  #eof setup()

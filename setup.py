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

import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    print("BuildStream requires setuptools in order to locate plugins. Install "
          "it using your package manager (usually python3-setuptools) or via "
          "pip (pip3 install setuptools).")
    sys.exit(1)

setup(name='BuildStream-external',
      version="0.1",
      description="A collection of BuildStream plugins that don't fit in with the core plugins for whatever reason.",
      license='LGPL',
      packages=find_packages(),
      install_requires=[
          'setuptools'
      ],
      package_data={
          'buildstream': [
              'elements/**.yaml'
          ]
      },
      entry_points={
          'buildstream.plugins': [
              'dpkg_build = elements.dpkg_build',
              'dpkg_deploy = elements.dpkg_deploy',
              'x86image = elements.x86image'
          ]
      })

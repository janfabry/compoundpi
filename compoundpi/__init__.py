# Copyright 2014 Dave Hughes <dave@waveform.org.uk>.
#
# This file is part of compoundpi.
#
# compoundpi is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# compoundpi is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# compoundpi.  If not, see <http://www.gnu.org/licenses/>.

"A project for controlling multiple Pi camera modules simultaneously"

import sys

__project__      = 'compoundpi'
__version__      = '0.1'
__keywords__     = ['raspberrypi', 'camera', 'multi']
__author__       = 'Dave Hughes'
__author_email__ = 'dave@waveform.org.uk'
__url__          = 'http://compoundpi.readthedocs.org/'
__platforms__    = 'ALL',

__requires__ = []

__extra_requires__ = {
    'client': [],
    'server': ['picamera'],
    'doc':    ['sphinx'],
    }

if sys.version_info[:2] == (3, 2):
    __extra_requires__['doc'].extend([
        # Particular versions are required for Python 3.2 compatibility.
        # The ordering is reverse because that's what easy_install needs...
        'Jinja<2.7',
        'MarkupSafe<0.16',
        ])

__classifiers__ = [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'Operating System :: POSIX',
    'Operating System :: Unix',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Topic :: Multimedia :: Graphics :: Capture',
    'Topic :: Scientific/Engineering',
    ]

__entry_points__ = {
    'console_scripts': [
        'cpid = compoundpi.server:main',
        'cpi = compoundpi.client:main',
        ],
    }

#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os

from setuptools import find_packages, setup

# Package meta-data.
NAME = 'stm32loader'
VERSION = "0.5.0"
DESCRIPTION = 'Flash firmware to STM32 microcontrollers using Python.'
URL = 'https://github.com/florisla/stm32loader'
EMAIL = 'florisla@gmail.com'
AUTHOR = 'Floris Lambrechts'
REQUIRES_PYTHON = '>=2.7.0'
PROJECT_URLS = {
    "Bug Tracker": "https://github.com/florisla/stm32loader/issues",
    "Source Code": "https://github.com/florisla/stm32loader",
}

REQUIRED = [
    'pyserial',
    'progress',
]

EXTRAS = {
    "dev": ['setuptools', 'wheel', 'twine', 'pylint', 'flake8', 'flake8-isort', 'black'],
}

HERE = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(HERE, 'README.md'), encoding='utf-8') as f:
        LONG_DESCRIPTION = '\n' + f.read()
except FileNotFoundError:
    LONG_DESCRIPTION = DESCRIPTION

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    project_urls=PROJECT_URLS,
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=('tests',)),
    entry_points={
        'console_scripts': ['stm32loader=stm32loader.__main__:main'],
    },
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license='GPL3',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Natural Language :: English',
        'Operating System :: OS Independent',
    ],
)

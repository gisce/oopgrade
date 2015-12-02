#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages


with open('README.rst') as readme_file:
    readme = readme_file.read()

dirname = os.path.dirname(__file__)

setup(
    name='oopgrade',
    version='0.2.0',
    description='Upgrade and migration tools',
    long_description=readme,
    author='GISCE-TI, S.L.',
    author_email='devel@gisce.net',
    url='https://github.com/gisce/oopgrade',
    packages=find_packages(),
    install_requires=[
        'semver'
    ],
    license='AGPL-3',
)

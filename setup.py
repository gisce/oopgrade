#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages


with open('README.md') as readme_file:
    readme = readme_file.read()

dirname = os.path.dirname(__file__)

setup(
    name='oopgrade',
    version='0.20.1',
    description='Upgrade and migration tools',
    long_description=readme,
    long_description_content_type="text/markdown",
    author='GISCE-TI, S.L.',
    author_email='devel@gisce.net',
    url='https://github.com/gisce/oopgrade',
    packages=find_packages(),
    install_requires=[
        'ooquery',
        'semver',
        'lxml',
        'python-sql>=1.0.0,<1.2.2',
        'six',
        'tqdm',
        'click',
        'pip',
        'osconf',
        'itsdangerous<2',
        'redis<3.6;python_version<="2.7.18"',
        'redis;python_version>"2.7.18"',
        'future',
    ],
    license='AGPL-3',
    entry_points='''
      [console_scripts]
      oopgrade=oopgrade.cli:oopgrade
    '''
)

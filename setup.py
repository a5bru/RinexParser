# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='rinex_parser',
    version='0.1.0',
    description='RinexParser',
    long_description=readme,
    author='Jürgen Fredriksson',
    author_email='juergen.fredriksson@bev.gv.at',
    url='https://github.com/dach.pos/rinexparser',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)

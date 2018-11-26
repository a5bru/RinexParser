# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

import setuptools


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license_text = f.read()

setuptools.setup(
    name='RinexParser',
    version='0.1.2.dev',
    description='Parsing Rinex files (supports version 2+3)',
    long_description=readme,
    author='Juergen Fredriksson',
    author_email='juergen.fredriksson@bev.gv.at',
    url='https://gitlab.com/dach.pos/rinexparser',
    license=license_text,
    # packages=['rinex_parser'],
    packages=setuptools.find_packages(exclude=('tests', 'docs', 'env', '.vscode')),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2.7",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
        "Operating System :: POSIX :: Linux",
    ]
)

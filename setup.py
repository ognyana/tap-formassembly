#!/usr/bin/env python

from setuptools import setup

setup(
    name='tap-formassembly',
    version="0.0.1",
    description='Singer.io tap for extracting data from the OrderHub API',
    author='Ognyana Ivanova',
    url='http://singer.io',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    py_modules=['tap_formassembly'],
    install_requires=[
        "singer-python",
        'requests',
        'backoff',
        'xmltodict',
        'nested-lookup'
   ],
    entry_points='''
       [console_scripts]
       tap-formassembly=tap_formassembly:main
    ''',
    packages=['tap_formassembly'],
    package_data = {
        "schemas": ["tap_formassembly/schemas/*.json"]
    },
    include_package_data=True
)

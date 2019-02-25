# -*- coding: utf-8 -*-
"""
Created on Mon Sep 24 16:05:28 2018

@author: danie
"""

from setuptools import find_packages, setup


setup(
    name='mbase_api',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'flask','numpy'
    ],
)
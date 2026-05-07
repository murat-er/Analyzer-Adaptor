#!/usr/bin/env python3
"""
Setup script for OPS Center Analyzer Adapter Python package.
"""

from setuptools import setup, find_packages


setup(
    name='ops-center-adapter',
    version='1.0.0',
    description='OPS Center Analyzer Adapter - Python Implementation',
    author='Hitachi Vantara',
    packages=find_packages(),
    install_requires=[
        'influxdb-client>=3.0.0',
        'requests>=2.28.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'mypy>=1.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'ops-center-adapter=ops_center_adapter.__main__:main',
        ],
    },
    python_requires='>=3.9',
)
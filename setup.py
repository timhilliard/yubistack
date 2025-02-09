#!/usr/bin/python
"""
A setuptools based setup module for YubiKit
"""

from setuptools import setup
from os import path
import re

here = path.abspath(path.dirname(__file__))


def get_version():
    """ Read the current version from __init__.py """
    with open('yubikit/__init__.py', 'rb') as initfile:
        for line in initfile.readlines():
            match = re.match(r"^__version__\s*=\s*['\"](.+)['\"]$", line.decode('utf-8'))
            if match:
                return match.group(1)
        raise RuntimeError("Unable to find version string.")


def get_long_description():
    """ Return the content of README """
    with open('README.rst', 'rb') as readmefile:
        return readmefile.read().decode('utf-8')


setup(
    name='yubikit',
    version=get_version(),
    description='Yubikit implementation',
    long_description=get_long_description(),
    url='https://github.com/timhilliard/yubikit',
    license='BSD 2 clause',
    author="Doug O'Riordan",
    author_email='oriordan@mail.be',

    packages=['yubikit'],
    install_requires=['pycryptodome', 'requests'],
    keywords='yubikey otp authentication',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Security :: Cryptography',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)

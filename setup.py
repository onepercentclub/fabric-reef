import os
from setuptools import setup

from fabric_reef import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

setup(
    name='fabric-reef',
    version=__version__,
    description='Fabric utils for Reef',
    author="1%Club Developers",
    author_email="devteam@onepercentclub.com",
    url="http://onepercentclub.com",
    packages=['fabric_reef'],
    install_requires=['fabric', 'GitPython'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Clustering',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities'
    ]
)


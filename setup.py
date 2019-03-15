#coding:utf-8
"""A setuptools based setup module for saturnin-sdk package.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# To use a consistent encoding
from codecs import open # pylint: disable=W0622
from os import path
# Always prefer setuptools over distutils
from setuptools import setup, find_packages

HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='saturnin-sdk',
    version='0.2',
    description='Reference implementation of Firebird Butler specification(s) in Python',
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url='https://github.com/FirebirdSQL/saturnin-sdk',
    author='Pavel Císař',
    author_email='pcisar@users.sourceforge.net',
    license='MIT',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',

        'Intended Audience :: Developers',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',

        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',

        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Object Brokering'
        ],
    keywords='Firebird Butler Services ZeroMQ Saturnin SDK',
    packages=find_packages(),  # Required
    zip_safe=False,
    install_requires=['pyzmq>=18.0.0', 'protobuf>=3.6.1'],
    python_requires='>=3.6, <4',
    test_suite='nose.collector',
    data_files=[],
    namespace_packages=['saturnin'],
    project_urls={
        'Documentation': 'https://saturnin-sdk.readthedocs.io',
        'Bug Reports': 'https://github.com/FirebirdSQL/saturnin-sdk/issues',
        'Funding': 'https://www.firebirdsql.org/en/donate/',
        'Source': 'https://github.com/FirebirdSQL/saturnin-sdk',
        },
    entry_points={'console_scripts': ['runner = saturnin.sdk.tools.runner:main',
                                     ],
                 }
)

#!/usr/bin/env python
#
# Copyright 2010 Andrew Fort
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import setuptools

# There is one additional pre-requisite package not available on pypi,
# tornadorpc.  You can install it manually from github, or using this
# command.

# $ pip install -e git+https://github.com/joshmarshall/tornadorpc.git@fda3e0e4f1d2a365e0e390bd783fe7d75619d25b#egg=tornadorpc-dev

tests_require=['mox']

setuptools.setup(
    name='notch.agent',
    version='0.4.10',
    description='The Network Operator\'s Toolkit for Command-line Hacking',
    entry_points = {
        'console_scripts': [
            'notch-agent = notch.agent.agent:main'
            ]
        },
    packages=['notch', 'notch.agent'],
    namespace_packages=['notch'],
    install_requires=['eventlet >= 0.9.6',
                      'ipaddr >= 2.0.0',
                      'jsonrpclib',
                      'paramiko >= 1.7.6',
                      'pexpect',
                      'PyYAML >= 3.0',
                      'tornado == 1.2.1',
                      'setuptools',
                      ],
    tests_require=tests_require,
    extras_require={'test': tests_require},
    test_suite='tests',
    url='http://code.google.com/p/notch/',
    author='Andrew Fort',
    author_email='notch-dev@googlegroups.com',
    license='http://www.apache.org/licenses/LICENSE-2.0',
    classifiers=['Development Status :: 2 - Pre-Alpha',
                 'Environment :: Console',
                 'Intended Audience :: System Administrators',
                 'License :: OSI Approved :: Apache Software License',
                 'Operating System :: POSIX',
                 'Programming Language :: Python :: 2.6',
                 'Topic :: System :: Networking :: Monitoring',
                 'Topic :: System :: Systems Administration',
                 ],
    zip_safe=True,
    )

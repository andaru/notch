#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.
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

"""Tests for the credential module."""


import os
import unittest

from notch.agent import credential
from notch.agent import errors


# Path to testdata root.
TESTDATA = os.path.join(os.path.dirname(__file__), 'testdata')


class TestCredential(unittest.TestCase):

    def testRegexpNeedsString(self):
        self.assertRaises(TypeError, credential.Credential, regexp=5)

    def testRegexpWithString(self):
        cred = credential.Credential(regexp='ar1.*',
                                     username='foo',
                                     password='bar')
        match = cred.regexp.match('ar1.foo')
        self.assert_(match is not None)
        match = cred.regexp.match('car1.foo')
        self.assert_(match is None)

        match = cred.matches('ar1.foo')
        self.assertEqual(match, True)
        match = cred.matches('car1.foo')
        self.assertEqual(match, False)

    def testRegexpWithAnchoredString(self):
        cred = credential.Credential(regexp='^ar1.*$',
                                     username='foo',
                                     password='bar')
        match = cred.regexp.match('ar1.foo')
        self.assert_(match is not None)
        match = cred.regexp.match('car1.foo')
        self.assert_(match is None)

        self.assertEqual(cred.matches('ar1.foo'), True)
        self.assertEqual(cred.matches('car1.foo'), False)
        self.assertEqual(cred.matches('abc2'), False)


class TestYamlCredentials(unittest.TestCase):

    def testCredsFile(self):
        creds = credential.load_credentials_file(
                os.path.join(TESTDATA, 'credentials1.yaml'))
        self.assertEqual(len(creds), 2)
        self.assertEqual(len(creds.credentials), 2)
        cred0 = creds.credentials[0]
        cred1 = creds.credentials[1]
        self.assertEqual(cred0.username, 'fred')
        self.assertEqual(cred0.regexp_string, '^ar.*$')
        self.assert_(cred0.connect_method is None)
        self.assertEqual(cred1.password, 'bar')
        self.assertEqual(cred1.enable_password, 'enable_bar')
        self.assertEqual(cred1.connect_method, 'sshv2')
        self.assert_(cred1.ssh_private_key is None)

    def testInvalidCredsFile1(self):
        self.assertRaises(TypeError, credential.load_credentials_file,
                          os.path.join(TESTDATA, 'invalid_credentials1.yaml'))

    def testCredsFileWithBlankFinalBlock(self):
        creds1 = credential.load_credentials_file(
                os.path.join(TESTDATA, 'credentials1.yaml'))
        
        creds2 = credential.load_credentials_file(
                os.path.join(TESTDATA, 'blank_final_group_credentials.yaml'))

        self.assertEqual(len(creds1), len(creds2))
        self.assertEqual(creds1.credentials[0],
                         creds2.credentials[0])
        self.assertEqual(creds1.credentials[1],
                         creds2.credentials[1])
        self.assertEqual(creds1.credentials[0],
                         creds2.get_credential('ar1.foo'))
        self.assertEqual(creds1.credentials[1],
                         creds2.get_credential('xr1.foo'))
        
    def testInvalidCredsFile2(self):
        self.assertRaises(errors.MissingFieldError,
                          credential.load_credentials_file,
                          os.path.join(TESTDATA, 'invalid_credentials2.yaml'))

    def testGetCredential(self):
        creds = credential.load_credentials_file(
                os.path.join(TESTDATA, 'credentials1.yaml'))
        self.assertEqual(creds.credentials[0], creds.get_credential('ar1.foo'))
        self.assertEqual(creds.credentials[1], creds.get_credential('xr1.foo'))

    def testGetCredentialInvalidInputs(self):
        creds = credential.load_credentials_file(
                os.path.join(TESTDATA, 'credentials1.yaml'))
        self.assertRaises(errors.NoMatchingCredentialError,
                          creds.get_credential, '')
        self.assertRaises(errors.NoMatchingCredentialError,
                          creds.get_credential, None)
        self.assertRaises(TypeError, creds.get_credential, 5)


if __name__ == '__main__':
    unittest.main()

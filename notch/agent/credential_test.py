#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Tests for the credential module."""


import os
import unittest

import credential


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
        self.assertEqual(cred1.password, 'bar')
        self.assertEqual(cred1.enable_password, 'enable_bar')
        self.assert_(cred1.ssh_private_key is None)

    def testInvalidCredsFile1(self):
        self.assertRaises(TypeError, credential.load_credentials_file,
                          os.path.join(TESTDATA, 'invalid_credentials1.yaml'))

    def testInvalidCredsFile2(self):
        self.assertRaises(credential.MissingFieldError,
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
        self.assert_(creds.get_credential('') is None)
        self.assert_(creds.get_credential(None) is None)
        self.assertRaises(TypeError, creds.get_credential, 5)


if __name__ == '__main__':
    unittest.main()

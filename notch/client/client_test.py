#!/usr/bin/env python
#
# Copyright 2010 Andrew Fort. All Rights Reserved.
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

"""Tests for the client module."""


import mox
import unittest
import os

import jsonrpclib

import client


class RequestTest(unittest.TestCase):

    def testValid(self):
        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'})
        self.assert_(r.valid)
        r = client.Request('', {})
        self.assert_(not r.valid)
        r = client.Request('command', {})
        self.assert_(not r.valid)
        r = client.Request('', {'device_name': 'localhost',
                                'command': 'show ver'})
        self.assert_(not r.valid)


class ConnectionTest(unittest.TestCase):

    def testSyncrhonousRequest(self):
        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).AndReturn('RouterOS 1.0')
        notch.command(command='help', device_name='localhost',
                      mode=None).AndReturn('Help goes here')
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch

        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'})
        result = nc.exec_request(r)
        self.assertEqual(result, 'RouterOS 1.0')

        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'help'})
        result = nc.exec_request(r)
        self.assertEqual(result, 'Help goes here')

        m.VerifyAll()

    def testAsyncrhonousRequest(self):
        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).AndReturn('RouterOS 1.0')
        notch.command(command='help', device_name='localhost',
                      mode=None).AndReturn('Help goes here')
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch

        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'})
        result = nc.exec_request(r)
        self.assertEqual(result, 'RouterOS 1.0')

        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'help'})
        result = nc.exec_request(r)
        self.assertEqual(result, 'Help goes here')

        m.VerifyAll()


if __name__ == '__main__':
    unittest.main()

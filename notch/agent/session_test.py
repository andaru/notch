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

"""Unit tests for session management."""


import mox
import unittest

import device
import errors
import session


class TestSessionWithoutDevice(unittest.TestCase):

    def setUp(self):
        self.session = session.Session()

    def testSessionDevice(self):
        self.assertTrue(self.session.device is None)

    def testConnected(self):
        self.assertFalse(self.session.connected)

    def testSessionConnectNoDevice(self):
        self.assertTrue(self.session.connect() is None)

    def testSessionDisconnectNoDevice(self):
        self.assertTrue(self.session.disconnect() is None)

    def testNoDeviceRaisesInvalidDeviceError(self):
        self.assertRaises(errors.InvalidDeviceError, self.session.request,
                          'command')

    def testInvalidMethodName(self):
        self.assertRaises(errors.InvalidRequestError, self.session.request,
                          'not_a_valid_method_name')


class TestSessionAbstractDevice(unittest.TestCase):

    def setUp(self):
        self.device = device.Device(name='test1.popname', addresses='10.0.0.1')
        self.session = session.Session(device=self.device)

    def testDeviceDetails(self):
        self.assertEqual(self.device.name, 'test1.popname')
        self.assertEqual(str(self.device.addresses[0]), '10.0.0.1')
        self.assertTrue(self.device.vendor is None)
        self.assertFalse(self.device.connected)

    def testRequestOnAbstractDevice(self):
        self.assertRaises(NotImplementedError,
                          self.session.request, 'command', None)
        self.assertRaises(NotImplementedError,
                          self.session.request, 'command', 'sh run')
        self.assertRaises(NotImplementedError,
                          self.session.request, 'command', 'sh run',
                          mode='shell')


class TestSessionMockDevice(unittest.TestCase):

    def setUp(self):
        self.mock = mox.Mox()

    def testConnect(self):
        dev = self.mock.CreateMock(device.Device)
        dev.connect(credential=None).AndReturn(None)
        self.mock.ReplayAll()
        s = session.Session(device=dev)
        s.connect()
        self.assertTrue(s.connected)
        self.mock.VerifyAll()

    def testDisconnect(self):
        dev = self.mock.CreateMock(device.Device)
        dev.connect(credential=None).AndReturn(None)
        dev.disconnect().AndReturn(None)
        self.mock.ReplayAll()
        s = session.Session(device=dev)
        dev.connected = False
        self.assertFalse(s.connected)
        s.connect()
        dev.connected = True
        self.assertTrue(s.connected)
        s.disconnect()
        dev.connected = False
        self.assertFalse(s.connected)
        self.mock.VerifyAll()

    def testCommandRequest(self):
        dev = self.mock.CreateMock(device.Device)
        dev.connect(credential=None).AndReturn(None)
        dev.command('show version').AndReturn('# Config data')
        self.mock.ReplayAll()
        s = session.Session(device=dev)
        result = s.request('command', 'show version')
        self.assertEqual(result, '# Config data')
        self.mock.VerifyAll()

    def testCommandRequestInShellMode(self):
        dev = self.mock.CreateMock(device.Device)
        dev.connect(credential=None).AndReturn(None)
        dev.command('show version', mode='shell').AndReturn('# Shell mode')
        self.mock.ReplayAll()
        s = session.Session(device=dev)
        result = s.request('command', 'show version', mode='shell')
        self.assertEqual(result, '# Shell mode')
        self.mock.VerifyAll()



if __name__ == '__main__':
    unittest.main()

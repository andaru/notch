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

"""Tests for the controller module."""

import adns
import ADNS
import ipaddr
import mox
import unittest

from notch.agent import device_manager
from notch.agent import errors
from notch.agent import controller
from notch.agent import session
from notch.agent.devices import device


class TestController(unittest.TestCase):

    def setUp(self):
        self.controller = controller.Controller()
        self.mock = mox.Mox()

    def tearDown(self):
        self.mock.UnsetStubs()

    def testSessionKey(self):
        sk = session.SessionKey(device_name='xr1.foo',
                                connect_method='sshv2',
                                user='anonymous',
                                privilege_level='ro')
        self.assertEqual(sk.device_name, 'xr1.foo')
        self.assertEqual(sk.connect_method, 'sshv2')
        self.assertEqual(sk.user, 'anonymous')
        self.assertEqual(sk.privilege_level, 'ro')
        return sk

    def testGetSession(self):
        sk = self.testSessionKey()
        dev = self.mock.CreateMock(device.Device)
        self.mock.ReplayAll()

        expected_session = session.Session(device=dev)
        self.controller.sessions = {sk: expected_session}

        sess = self.controller.get_session(device_name='xr1.foo',
                                           connect_method='sshv2',
                                           user='anonymous',
                                           privilege_level='ro')
        self.assertEqual(sess, expected_session)
        self.mock.VerifyAll()

    def testCreateSession(self):
        sk = session.SessionKey(device_name='xr1.foo',
                                connect_method='sshv2',
                                user='anonymous',
                                privilege_level='ro')
        dev1 = device_manager.DeviceInfo(device_name='xr1.foo',
                                         device_type='juniper',
                                         addresses=('10.0.0.1', ))
        self.dm = self.mock.CreateMock(device_manager.DeviceManager)
        self.controller.device_manager = self.dm
        response = (adns.status.ok, None, None, ('10.0.0.1', ))
        self.dm.device_info('xr1.foo').AndReturn(dev1)
        self.dm.device_info('xr1.foo').AndReturn(dev1)
        self.mock.ReplayAll()
        sess = self.controller.create_session(sk)
        self.assertEqual(sess.device.name, 'xr1.foo')
        self.assertEqual(sess.device.addresses, [ipaddr.IPAddress('10.0.0.1')])
        self.assertEqual(sess.connected, False)
        get_sess = self.controller.get_session(device_name='xr1.foo',
                                               connect_method='sshv2',
                                               user='anonymous',
                                               privilege_level='ro')
        self.assertEqual(sess, get_sess)
        self.mock.VerifyAll()

    def testRequest(self):
        sk = session.SessionKey(device_name='xr1.foo',
                                connect_method='sshv2',
                                user='anonymous',
                                privilege_level='ro')

        sess = self.mock.CreateMock(session.Session)
        sess.request('command', command='show run', connect_method='sshv2',
                     device_name='xr1.foo', mode='shell',
                     privilege_level='ro', user='anonymous'
                     ).AndReturn('# show run output.')

        self.mock.ReplayAll()
        self.controller.sessions = {sk: sess}
        resp = self.controller.request('command',
                                       command='show run',
                                       mode='shell',
                                       device_name='xr1.foo',
                                       connect_method='sshv2',
                                       user='anonymous',
                                       privilege_level='ro')
        self.assertEqual(resp, '# show run output.')
        self.mock.VerifyAll()

    def testRequestNoDeviceName(self):
        sk = session.SessionKey(device_name=None,
                                connect_method=None,
                                user=None,
                                privilege_level=None)
        sess = self.mock.CreateMock(session.Session)
        self.mock.ReplayAll()
        self.controller.sessions = {sk: sess}
        self.assertRaises(ValueError, self.controller.request, 'command',
                          command='show run')
        self.mock.VerifyAll()

    def testRequestNoSessionCreated(self):
        sk = session.SessionKey(device_name='xr1.foo',
                                connect_method=None,
                                user=None,
                                privilege_level=None)
        sess = self.mock.CreateMock(session.Session)
        self.mock.ReplayAll()
        self.controller.sessions = {sk: sess}
        # Invalid name (so address lookup fails and no session created).
        self.assertRaises(errors.NoSessionCreatedError, self.controller.request,
                          'command', command='show run', device_name='___')
        self.mock.VerifyAll()

    def testExpireSession(self):
        dev = self.mock.CreateMock(device.Device)
        dev.name = 'xr1.foo'
        dev.vendor = 'junos'
        dev.connect(credential=None).AndReturn(None)
        dev.disconnect().AndReturn(None)
        self.mock.ReplayAll()
        sess = session.Session(device=dev)
        sess.connect()
        self.controller.expire_session(None, sess)
        # No value assertions, just confirm all the device calls are made.
        self.mock.VerifyAll()


if __name__ == '__main__':
    unittest.main()

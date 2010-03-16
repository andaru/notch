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
from eventlet.green import time

import jsonrpclib

import client

class CommandError(Exception):
    """An error occured executing the command on the host."""


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

    def testSetup(self):
        nc = client.Connection('localhost:1')
        self.assert_(nc)
        self.assertRaises(client.NoSuchLoadBalancingPolicyError,
                          client.Connection, 'localhost:1',
                          load_balancing_policy='does not exist')

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
        r = nc.exec_request(r)
        self.assertEqual(r.result, 'RouterOS 1.0')

        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'help'})
        r = nc.exec_request(r)
        self.assertEqual(r.result, 'Help goes here')

        m.VerifyAll()

    def testAsyncrhonousRequest(self):
        def cb(r):
            self._r = r

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
                                       'command': 'show ver'},
                           callback=cb)
        result = nc.exec_request(r)
        nc.wait_all()
        self.assertEqual(self._r.result, 'RouterOS 1.0')

        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'help'},
                           callback=cb)
        result = nc.exec_request(r)
        nc.wait_all()
        self.assertEqual(self._r.result, 'Help goes here')

        m.VerifyAll()

    def testRequestTimeoutSync(self):
        def delay(command=None, device_name=None, mode=None):
            time.sleep(0.5)
        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).WithSideEffects(delay).AndReturn(
            'RouterOS 1.0')
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch
        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'},
                           timeout_s=0.1)
        self.assertRaises(client.TimeoutError, nc.exec_request, r)
        m.VerifyAll()

    def testRequestTimeoutAsync(self):
        def delay(command=None, device_name=None, mode=None):
            time.sleep(0.5)

        def cb(r):
            self._r = r

        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).WithSideEffects(delay).AndReturn(
            'RouterOS 1.0')
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch
        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'},
                           callback=cb,
                           timeout_s=0.1)
        _ = nc.exec_request(r)
        # Wait around for the timeout to occur.
        self.assertRaises(client.TimeoutError, nc.wait_all)
        m.VerifyAll()

    def testTimeoutDoesNotOccurSync(self):
        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).AndReturn('RouterOS 1.0')
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch
        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'},
                           timeout_s=1)
        self.assert_(not r.completed)
        self.assertEqual(nc.exec_request(r).result, 'RouterOS 1.0')
        self.assert_(r.completed)
        m.VerifyAll()

    def testErrorOccuredSync(self):
        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).AndRaise(CommandError)
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch
        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'},
                           timeout_s=1)
        
        result = nc.exec_request(r)
        self.assert_(isinstance(result.error, CommandError))
        self.assert_(r.completed)
        m.VerifyAll()

    def testErrorOccuredAsync(self):
        def cb(r):
            self.assert_(isinstance(r.error, CommandError))

        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).AndRaise(CommandError)
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch
        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'},
                           timeout_s=1, callback=cb)
        
        result = nc.exec_request(r)
        nc.wait_all()
        self.assert_(r.completed)
        m.VerifyAll()


if __name__ == '__main__':
    unittest.main()

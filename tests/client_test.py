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


import base64
import copy
import os

import mox
import unittest

from eventlet.green import time

import jsonrpclib

from notch.client import client


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

    def testCopiesAreMutable(self):
        r = client.Request('command', {'command': 'show ver'})
        r1 = copy.copy(r)
        r2 = copy.copy(r)
        r1.arguments['device_name'] = 'sw1.abc'
        r2.arguments['device_name'] = 'br3.xyz'
        self.assertEqual('sw1.abc', r1.arguments.get('device_name'))
        self.assertEqual('br3.xyz', r2.arguments.get('device_name'))

    def testCopiesWithoutMagicAreNotMutable(self):
        r = client.Request('command', {'command': 'show ver'})
        # Disable the magic copy method.
        client.Request.__copy__ = None
        r1 = copy.copy(r)
        r2 = copy.copy(r)
        r1.arguments['device_name'] = 'br3.xyz'
        r2.arguments['device_name'] = 'sw1.abc'
        # r1's unique value is lost, because r1 and r2's .argument
        # attributes are references to the same dict.
        self.assertEqual('sw1.abc', r1.arguments.get('device_name'))
        self.assertEqual('sw1.abc', r2.arguments.get('device_name'))

    def testDeepCopiesAreMutable(self):
        r = client.Request('command', {'command': 'show ver'})
        r1 = copy.deepcopy(r)
        r2 = copy.deepcopy(r)
        r1.arguments['device_name'] = 'sw1.abc'
        r2.arguments['device_name'] = 'br3.xyz'
        self.assertEqual('sw1.abc', r1.arguments.get('device_name'))
        self.assertEqual('br3.xyz', r2.arguments.get('device_name'))

    def testDeepCopiesWithoutMagicAreStillMutable(self):
        r = client.Request('command', {'command': 'show ver'})
        # Disable the magic copy method.
        client.Request.__copy__ = None
        client.Request.__deepcopy__ = None
        r1 = copy.deepcopy(r)
        r2 = copy.deepcopy(r)
        r1.arguments['device_name'] = 'br3.xyz'
        r2.arguments['device_name'] = 'sw1.abc'
        self.assertEqual('br3.xyz', r1.arguments.get('device_name'))
        self.assertEqual('sw1.abc', r2.arguments.get('device_name'))
       

class ConnectionTest(unittest.TestCase):
    """Tests for the Notch Agent JSON-RPC Connection class."""

    def testSetup(self):
        nc = client.Connection('localhost:1')
        self.assert_(nc)
        self.assertRaises(client.NoSuchLoadBalancingPolicyError,
                          client.Connection, 'localhost:1',
                          load_balancing_policy='does not exist')

    def testSyncrhonousRequest(self):
        m = mox.Mox()
        # `notch` in tests below refers to the jsonrpclib Proxy
        # instance. Mock out the responses to limit the test scope to
        # the client code only.
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).AndReturn('RouterOS 1.0')
        notch.command(command='help', device_name='localhost',
                      mode=None).AndReturn('Help goes here')
        notch.command(command='show version and blame',
                      device_name='localhost', mode=None).AndReturn(
            'Too many names...')
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        # Swap in mock the easy way.
        nc._notch = notch

        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'show ver'})
        r = nc.exec_request(r)
        self.assertEqual(r.result, 'RouterOS 1.0')

        r = client.Request('command', {'device_name': 'localhost',
                                       'command': 'help'})
        r = nc.exec_request(r)
        self.assertEqual(r.result, 'Help goes here')

        self.assertEqual(nc.command('localhost', 'show version and blame'),
                         'Too many names...')

        m.VerifyAll()

    def testAsyncrhonousRequest(self):
        def cb(r):
            self._r = r

        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).AndReturn(base64.b64encode('RouterOS 1.0'))
        notch.command(command='help', device_name='localhost',
                      mode=None).AndReturn(base64.b64encode('Help goes here'))
        notch.command(command='show version and blame',
                      device_name='localhost',
                      mode=None).AndReturn(base64.b64encode('Too many names...'))
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

        nc.command('localhost', 'show version and blame',
                   callback=cb)
        nc.wait_all()
        self.assertEqual(self._r.result, 'Too many names...')

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

    def testDevicesMatching(self):
        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.devices_matching(regexp='l.*').AndReturn(['localhost'])
        notch.devices_matching(regexp='.*l.*').AndReturn(['localhost',
                                                           'foo.local'])
        notch.devices_matching(regexp='^f.*').AndReturn(['foo.local'])

        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch
        r = client.Request('devices_matching', {'regexp': 'l.*'})
        result = nc.exec_request(r)
        nc.wait_all()
        self.assertEqual(result.result, ['localhost'])

        r = client.Request('devices_matching', {'regexp': '.*l.*'})
        result = nc.exec_request(r)
        nc.wait_all()
        self.assertEqual(result.result, ['localhost', 'foo.local'])

        self.assertEqual(nc.devices_matching('^f.*'), ['foo.local'])

    def testCounters(self):
        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost',
                      mode=None).AndReturn('RouterOS 1.0')
        notch.command(command='show ver and die', device_name='localhost',
                      mode=None).AndRaise(CommandError)
        m.ReplayAll()

        nc = client.Connection('localhost:1')
        nc._notch = notch

        r1 = client.Request('command', {'device_name': 'localhost',
                                        'command': 'show ver'})
        r2 = client.Request('command', {'device_name': 'localhost',
                                        'command': 'show ver and die'})
        r3 = client.Request('unknown', {'foo': 'bar',
                                        'command': 'who cares'})
        
        _ = nc.exec_request(r1)
        _ = nc.exec_request(r2)
        self.assertRaises(client.UnknownCommandError, nc.exec_request, r3)
        self.assertEqual(nc.counters.req_total, 3)
        self.assertEqual(nc.counters.req_ok, 2)        
        self.assertEqual(nc.counters.req_error, 1)
        self.assertEqual(nc.counters.resp_total, 2)
        self.assertEqual(nc.counters.resp_ok, 1)        
        self.assert_(nc.counters.resp_bytes == len('RouterOS 1.0'))
        self.assertEqual(nc.counters.resp_error, 1)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python
#
# Copyright 2010 Andrew Fort. All Rights Reserved.

"""Tests for the client module."""


import mox
import unittest
import os

import jsonrpclib

import client


class NotchRequestTest(unittest.TestCase):

    def testValid(self):
        r = client.NotchRequest('command', {'device_name': 'localhost',
                                            'command': 'show ver'})
        self.assert_(r.valid)
        r = client.NotchRequest('', {})
        self.assert_(not r.valid)
        r = client.NotchRequest('command', {})
        self.assert_(not r.valid)
        r = client.NotchRequest('', {'device_name': 'localhost',
                                     'command': 'show ver'})
        self.assert_(not r.valid)


class NotchClientTest(unittest.TestCase):

    def testSyncrhonousRequest(self):
        m = mox.Mox()
        notch = m.CreateMockAnything()
        notch.command(command='show ver', device_name='localhost', 
                      mode=None).AndReturn('RouterOS 1.0')
        notch.command(command='help', device_name='localhost', 
                      mode=None).AndReturn('Help goes here')
        m.ReplayAll()

        nc = client.NotchClient('localhost:1')
        nc._notch = notch

        r = client.NotchRequest('command', {'device_name': 'localhost',
                                            'command': 'show ver'})
        result = nc.exec_request(r)
        self.assertEqual(result, 'RouterOS 1.0')

        r = client.NotchRequest('command', {'device_name': 'localhost',
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

        nc = client.NotchClient('localhost:1')
        nc._notch = notch

        r = client.NotchRequest('command', {'device_name': 'localhost',
                                            'command': 'show ver'})
        result = nc.exec_request(r)
        self.assertEqual(result, 'RouterOS 1.0')

        r = client.NotchRequest('command', {'device_name': 'localhost',
                                            'command': 'help'})
        result = nc.exec_request(r)
        self.assertEqual(result, 'Help goes here')

        m.VerifyAll()

        
if __name__ == '__main__':
    unittest.main()

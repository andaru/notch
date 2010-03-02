#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Tests for the device module."""

import ipaddr

import mox
import unittest

import errors
import device


class TestDevice(unittest.TestCase):
    """Tests concrete methods in device.Device().

    Remaining methods are tested in session_test module using a mock.
    """

    def setUp(self):
        self.mock = mox.Mox()

    def tearDown(self):
        self.mock.UnsetStubs()

    def testDeviceConnect(self):
        dev = self.mock.CreateMock(device.Device)
        def set_connected():
            dev.connected = True
        dev.connect().WithSideEffects(set_connected).AndReturn(None)
        self.mock.ReplayAll()
        dev.connect()
        self.assertTrue(dev.connected)
        self.mock.VerifyAll()

    def testDeviceDisconnect(self):
        dev = self.mock.CreateMock(device.Device)
        def set_connected():
            dev.connected = True
        def set_disconnected():
            dev.connected = False
        dev.connect().WithSideEffects(set_connected).AndReturn(None)
        dev.disconnect().WithSideEffects(set_disconnected).AndReturn(None)
        self.mock.ReplayAll()
        dev.connect()
        self.assertTrue(dev.connected)
        dev.disconnect()
        self.assertFalse(dev.connected)
        self.mock.VerifyAll()

    def testDeviceAddressesProperty(self):
        dev = device.Device()
        self.assertEqual(dev.addresses, [])

        def set_valid():
            dev.addresses = ['10.0.0.1']

        def set_invalid_1():
            dev.addresses = ['10.0.0.1/32']

        def set_invalid_2():
            dev.addresses = ['10.0.0.0/24']

        def del_invalid():
            del dev.addresses

        self.assertRaises(ipaddr.Error, set_invalid_1)
        self.assertRaises(ipaddr.Error, set_invalid_2)
        set_valid()
        self.assertEqual(dev.addresses, [ipaddr.IPAddress('10.0.0.1')])
        self.assertRaises(AttributeError, del_invalid)

    def testDeviceSetupDefaults(self):
        dev = device.Device()
        self.assertEqual(dev.addresses, [])
        self.assert_(dev.name is None)
        self.assert_(dev.vendor is None)

    def testDeviceSetupValidAddress(self):
        dev = device.Device(addresses='10.0.0.1')
        self.assertEqual(dev.addresses, [ipaddr.IPAddress('10.0.0.1')])

    def testDeviceSetupInvalidAddresses(self):
        # 10.0.0.1/32 denotes a network, not an address (technically).
        dev = device.Device(addresses=['10.0.0.1/32'])
        self.assertEqual(dev.addresses, [])
        # 10.0.0.1/24 denotes a network.
        dev = device.Device(addresses=['10.0.0.1/24'])
        self.assertEqual(dev.addresses, [])

    def testDeviceSetupInvalidAddressCausesConnectError(self):
        # 10.0.0.1/32 denotes a network, not an address (technically).
        fake_dev = device.Device(addresses=['10.0.0.1/32'])
        self.assertEqual(fake_dev.addresses, [])
        self.assertRaises(errors.DeviceWithoutAddressError, fake_dev.connect)


if __name__ == '__main__':
    unittest.main()

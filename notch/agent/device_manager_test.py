#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Tests for the device_manager module."""


import adns
import ADNS

import mox
import unittest
import os

import device_manager
import notch_config


# Path to testdata root.
TESTDATA = os.path.join(os.path.dirname(__file__), 'testdata')


class DeviceManagerTest(unittest.TestCase):

    def testDeviceManagerReadConfigValid1(self):
        config = notch_config.get_config_from_file(
            os.path.join(TESTDATA, 'notch_config.yaml'))
        self.device_manager = device_manager.DeviceManager(config)
        self.assertEqual(len(self.device_manager.providers), 2)
        self.assert_(self.device_manager.provider('old_rancid_configs'))
        self.assert_(self.device_manager.provider('internal_dns'))

        self.assertEqual(
            self.device_manager.provider('old_rancid_configs').root,
            'testdata/router_db/')
        self.assertEqual(
            self.device_manager.provider('old_rancid_configs'
                                          ).ignore_down_devices, True)

    def testAddressLookup(self):
        self.mock = mox.Mox()
        self.adns = self.mock.CreateMock(ADNS.QueryEngine)
        self.dp = device_manager.DeviceProvider()
        self.dp._dns = self.adns
        response1 = (adns.status.ok, None, None, ('10.0.0.1', ))
        self.adns.synchronous('xr1.foo', adns.rr.A).AndReturn(response1)
        response2 = (adns.status.ok, None, None, ('10.0.0.2', '10.0.0.3'))
        self.adns.synchronous('xr2.foo', adns.rr.A).AndReturn(response2)

        self.mock.ReplayAll()
        self.assertEqual(self.dp.address_lookup('xr1.foo'),
                         ('10.0.0.1', ))
        self.assertEqual(self.dp.address_lookup('xr2.foo'),
                         ('10.0.0.2', '10.0.0.3'))
        self.mock.VerifyAll()

    def testProvider(self):
        config = notch_config.get_config_from_file(
            os.path.join(TESTDATA, 'notch_config.yaml'))
        self.device_manager = device_manager.DeviceManager(config)
        self.assert_(self.device_manager.provider('old_rancid_configs'))
        self.assert_(self.device_manager.provider('internal_dns'))
        self.assertEqual(
            self.device_manager.provider('old_rancid_configs').name,
            'router.db')
        self.assertEqual(self.device_manager.provider('internal_dns').name,
                         'dnstxt')
        # Unknown providers return None.
        self.assertEqual(None, self.device_manager.provider('unknown'))
        self.assertEqual(None, self.device_manager.provider(''))
        self.assertEqual(None, self.device_manager.provider(None))
        self.assertEqual(None, self.device_manager.provider(0))

    def testAddProviders(self):
        self.device_manager = device_manager.DeviceManager({})
        self.device_manager.add_providers(None)
        self.assertEqual(self.device_manager.serve_ready, False)
        self.device_manager.add_providers({})
        self.assertEqual(self.device_manager.serve_ready, False)

    def testScanProviders(self):
        config = notch_config.get_config_from_file(
            os.path.join(TESTDATA, 'notch_config.yaml'))
        self.device_manager = device_manager.DeviceManager(config)
        self.device_manager.scan_providers()
        self.assertEqual(self.device_manager.serve_ready, True)
        self.device_manager.scan_providers()
        self.assertEqual(self.device_manager.serve_ready, True)

    def testDeviceInfo(self):
        self.mock = mox.Mox()
        self.adns = self.mock.CreateMock(ADNS.QueryEngine)
      
        response1 = (adns.status.ok, None, None, ('10.0.0.1', ))
        self.adns.synchronous('xr1.foo', adns.rr.A).AndReturn(response1)
        response2 = (adns.status.ok, None, None, ('10.0.0.2', ))
        self.adns.synchronous('lr1.foo', adns.rr.A).AndReturn(response2)
        response3 = (adns.status.ok, None, None, ('10.0.0.2', '10.0.0.3'))
        self.adns.synchronous('xr2.foo', adns.rr.A).AndReturn(response3)
        self.mock.ReplayAll()

        config = notch_config.get_config_from_file(
            os.path.join(TESTDATA, 'notch_config.yaml'))
        self.device_manager = device_manager.DeviceManager(config)
        self.device_manager.providers[(100, 'old_rancid_configs')]._dns = (
            self.adns)
        self.device_manager.providers[(105, 'internal_dns')]._dns = (
            self.adns)

        self.assertEqual(self.device_manager.device_info('xr2.foo').device_name,
                         'xr2.foo')
        self.assertEqual(self.device_manager.device_info('xr2.foo').device_type,
                         'juniper')
        self.assertEqual(self.device_manager.device_info('lr1.foo').addresses,
                         ('10.0.0.2', ))
        self.assertEqual(self.device_manager.device_info('lr1.foo').device_type,
                         'cisco')
        self.mock.VerifyAll()


class TestRancidDeviceProvider(unittest.TestCase):

    def setUp(self):
        self.mock = mox.Mox()
        self.dns = self.mock.CreateMock(ADNS.QueryEngine)

    def testRancidDeviceProviderNormal(self):
        # There are 3 valid devices in the router.db files, one of which
        # is down, so we only see two lines here.
        response1 = (adns.status.ok, None, None, ('10.0.0.1', ))
        self.dns.synchronous('xr1.foo', adns.rr.A).AndReturn(response1)
        response2 = (adns.status.ok, None, None, ('10.0.0.2', ))
        self.dns.synchronous('lr1.foo', adns.rr.A).AndReturn(response2)

        self.mock.ReplayAll()
        rancid_provider = device_manager.RancidDeviceProvider(
            root=TESTDATA)
        rancid_provider._dns = self.dns
        rancid_provider.scan()
        self.assertEqual(len(rancid_provider.devices), 2)
        self.mock.VerifyAll()

    def testRancidDeviceProviderAllowDown(self):
        # There are 3 valid devices in the router.db files, one of which
        # is down, so we only see two lines here.
        response1 = (adns.status.ok, None, None, ('10.0.0.1', ))
        self.dns.synchronous('xr1.foo', adns.rr.A).AndReturn(response1)
        response2 = (adns.status.ok, None, None, ('10.0.0.2', ))
        self.dns.synchronous('lr1.foo', adns.rr.A).AndReturn(response2)
        response3 = (adns.status.ok, None, None, ('10.0.0.3', ))
        self.dns.synchronous('xr2.foo', adns.rr.A).AndReturn(response3)
        self.mock.ReplayAll()

        rancid_provider = device_manager.RancidDeviceProvider(
            root=TESTDATA, ignore_down_devices=True)
        rancid_provider._dns = self.dns
        rancid_provider.scan()
        self.assertEqual(len(rancid_provider.devices), 3)
        self.assert_('10.0.0.1' in rancid_provider.devices['xr1.foo'].addresses)
        self.assert_('10.0.0.2' in rancid_provider.devices['lr1.foo'].addresses)
        self.assert_('10.0.0.3' in rancid_provider.devices['xr2.foo'].addresses)
        self.mock.VerifyAll()


if __name__ == '__main__':
    unittest.main()

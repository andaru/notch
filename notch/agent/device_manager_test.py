#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Tests for the device_manager module."""


import unittest
import os
import socket
import sys

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

    def _mock_gethostbyname(self, host):
        if host == 'xr1.foo':
            return ['10.0.0.1']
        elif host == 'xr2.foo':
            return ['10.0.0.2', '10.0.0.3']
        elif host == 'lr1.foo':
            return ['10.0.0.2']

    def testAddressLookup(self):
        dp = device_manager.DeviceProvider()
        device_manager.socket.gethostbyname = self._mock_gethostbyname

        self.assertEqual(dp.address_lookup('xr1.foo'), ['10.0.0.1'])

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
            os.path.join(TESTDATA, 'simple_config.yaml'))
        self.device_manager = device_manager.DeviceManager(config)
        self.assertEqual(self.device_manager.serve_ready, False)
        self.device_manager.scan_providers()
        self.assertEqual(self.device_manager.serve_ready, True)
        self.device_manager.scan_providers()
        self.assertEqual(self.device_manager.serve_ready, True)

    def testDeviceInfo(self):
        device_manager.socket.gethostbyname = self._mock_gethostbyname
        config = notch_config.get_config_from_file(
            os.path.join(TESTDATA, 'simple_config.yaml'))
        dm = device_manager.DeviceManager(config)
        self.assertEqual(dm.serve_ready, False)
        dm.scan_providers()
        self.assertEqual(dm.serve_ready, True)
        xr2_foo = device_manager.DeviceInfo(
            device_name='xr2.foo',
            addresses=['10.0.0.2', '10.0.0.3'],
            device_type='juniper')
        self.assertEqual(dm.device_info('xr2.foo'), xr2_foo)
        self.assertEqual(dm.device_info('xr1.foo').addresses, ['10.0.0.1'])
        self.assertEqual(dm.device_info('lr1.foo').device_type, 'cisco')

    def testMatchingDevices(self):
        device_manager.socket.gethostbyname = self._mock_gethostbyname
        config = notch_config.get_config_from_file(
            os.path.join(TESTDATA, 'simple_config.yaml'))
        dm = device_manager.DeviceManager(config)
        self.assertEqual(dm.serve_ready, False)
        dm.scan_providers()
        self.assertEqual(dm.serve_ready, True)

        all = dm.devices_matching(r'.*')
        for d in ('lr1.foo', 'xr1.foo', 'xr2.foo'):
            self.assert_(d in all, '%s not in %s' % (d, all))

        devs = dm.devices_matching(r'^$')
        self.assert_(not devs)

        devs = dm.devices_matching(r'lr.*')
        self.assert_('lr1.foo' in devs)
        
        devs = dm.devices_matching(r'xr.*')
        self.assert_('xr1.foo' in devs)
        self.assert_('xr2.foo' in devs)

        devs = dm.devices_matching(r'^..1\.foo$')
        self.assert_('lr1.foo' in devs)
        self.assert_('xr1.foo' in devs)


class TestRancidDeviceProvider(unittest.TestCase):

    def _mock_gethostbyname(self, host):
        if host == 'xr1.foo':
            return ['10.0.0.1']
        elif host == 'xr2.foo':
            return ['10.0.0.3']
        elif host == 'lr1.foo':
            return ['10.0.0.2']

    def testRancidDeviceProviderNormal(self):
        device_manager.socket.gethostbyname = self._mock_gethostbyname

        rancid_provider = device_manager.RancidDeviceProvider(
            root=TESTDATA)
        rancid_provider.scan()
        self.assertEqual(len(rancid_provider.devices), 2)

    def testRancidDeviceProviderAllowDown(self):
        device_manager.socket.gethostbyname = self._mock_gethostbyname

        rancid_provider = device_manager.RancidDeviceProvider(
            root=TESTDATA, ignore_down_devices=True)
        rancid_provider.scan()
        self.assertEqual(len(rancid_provider.devices), 3)
        self.assert_('10.0.0.1' in rancid_provider.devices['xr1.foo'].addresses)
        self.assert_('10.0.0.2' in rancid_provider.devices['lr1.foo'].addresses)
        self.assert_('10.0.0.3' in rancid_provider.devices['xr2.foo'].addresses)


if __name__ == '__main__':
    unittest.main()

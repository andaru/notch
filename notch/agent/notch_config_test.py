#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Tests for the notch_config module."""


import os
import unittest

import notch_config


# Path to testdata root.
TESTDATA = os.path.join(os.path.dirname(__file__), 'testdata')


class NotchConfigTest(unittest.TestCase):

    def testYamlConfigFileMissingOptionsSection(self):
        self.assertRaises(notch_config.ConfigMissingRequiredSectionError,
                          notch_config.load_config_file,
                          os.path.join(TESTDATA, 'invalid_config1.yaml'))

    def testUnknownConfigFile(self):
        self.assertRaises(notch_config.UnknownConfigurationFileFormatError,
                          notch_config.load_config_file,
                          os.path.join(TESTDATA, 'unknown_config_format.xml'))

    def testEmptyConfigFile(self):
        self.assertRaises(notch_config.ConfigMissingRequiredSectionError,
                          notch_config.load_config_file,
                          os.path.join(TESTDATA, 'empty_config.yaml'))

    def testNotYamlFile(self):
        self.assertRaises(notch_config.ConfigMissingRequiredSectionError,
                          notch_config.load_config_file,
                          os.path.join(TESTDATA, 'not_really_yaml.yaml'))

    def testNonExistantFile(self):
        self.assertEqual(
            notch_config.load_config_file(
                os.path.join(TESTDATA, 'file_is_not_there.yaml')).loaded,
            False)
        self.assertEqual(
            notch_config.load_config_file(
                os.path.join(TESTDATA, 'file_is_not_there.yaml')).config_file,
            None)
        self.assertEqual(
            notch_config.get_config_from_file(
                os.path.join(TESTDATA, 'file_is_not_there.yaml')),
            {})

    def testYamlConfigFileValid1(self):
        config = notch_config.load_config_file(
            os.path.join(TESTDATA, 'device_config1.yaml'))
        devs = config.config['device_sources']
        self.assertEqual(devs['old_rancid_configs']['ignore_down_devices'],
                         True)
        self.assertEqual(devs['old_rancid_configs']['provider'], 'router.db')

    def testYamlConfigFileValid2(self):
        config = notch_config.load_config_file(
            os.path.join(TESTDATA, 'notch_config.yaml'))
        devs = config.config['device_sources']
        self.assertEqual(devs['old_rancid_configs']['ignore_down_devices'],
                         True)
        self.assertEqual(devs['old_rancid_configs']['provider'], 'router.db')
        options = config.config['options']
        self.assertEqual(options['port'], 8000)
        self.assertEqual(options['max_threads'], 128)

    def testGetConfigFromFile(self):
        config = notch_config.get_config_from_file(
            os.path.join(TESTDATA, 'notch_config.yaml'))
        self.assert_(config['device_sources'])
        self.assertEqual(config['device_sources']['old_rancid_configs']
                         ['root'], 'testdata/router_db/')


if __name__ == '__main__':
    unittest.main()

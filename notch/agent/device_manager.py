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

"""Notch Device Manager.

The device manager manages device metadata for devices known to Notch.
It also provides an API for importing and exporting device metadata
from other sources, such as RANCID router.db files.

Without this subsystem, device vendor information would have to be submitted
by every client RPC.
"""

import yaml
import collections
import logging
import os
import re
# Import the greened socket class for async DNS lookups.
from eventlet.green import socket

import device_factory
import lru


# Information about a device, provided by the device_info
# pylint:disable-msg=C0103
DeviceInfo = collections.namedtuple('DeviceInfo',
                                    'device_name addresses device_type')


class DeviceProvider(object):
    """An abstract provider of device information."""

    # Override this in sub-classes.
    name = '__abstract__'

    def __init__(self, **kwargs):
        """Use only keyword arguments in sub-class initialisers."""
        self._match_cache = lru.LruDict(self._populate_match_cache)
        # DeviceInfo instances keyed by device name.
        self.devices = {}
        self.ready = False

    def _populate_match_cache(self, reg):
        try:
            regexp = re.compile(reg, re.I)
        except:
            return frozenset()
        else:
            result = set()
            for device in self.devices.keys():
                if regexp.match(device):
                    result.add(device)
            return result

    def address_lookup(self, name):
        """Performs a synchronous DNS lookup for the requested address.

        Args:
          name: A string, a hostname to lookup in the DNS.

        Returns:
          A list of one or more IPv4 dotted-quad address strings.

        Raises:
          socket.gaierror: If there was an error during DNS lookup.
        """
        return socket.gethostbyname(name)

    def scan(self):
        """Performs a scan over the source information.

        This method should set up any instance state required for the
        device_info callback to answer queries.
        """
        self.ready = True

    def device_info(self, device_name):
        """Returns any known information about a single requested device.

        Fields that are not known in the response should be set to None.

        Args:
          device_name: A string, the device name to return info for.

        Returns:
          A DeviceInfo namedtuple or;
          None if the device was not found.
        """
        return self.devices.get(device_name)

    def devices_matching(self, reg):
        return self._match_cache[reg]


class RancidDeviceProvider(DeviceProvider):
    """A provider of devices sourced from RANCID router.db files.

    DNS is queried to populate the addresses properties in responses.
    """

    name = 'router.db'

    re_router_db_line = re.compile(r'([^:]+):([^:]+):([^:]+)?:?([^:#]+?)?')

    def __init__(self, root=None, ignore_down_devices=False, **kwargs):
        super(RancidDeviceProvider, self).__init__(**kwargs)
        self.root = root
        self.ignore_down_devices = ignore_down_devices
        if root is None:
            raise ValueError('%s requires "root" keyword argument.'
                             % self.__class__.__name__)

    def _read_router_db(self, router_db):
        """Reads the router.db file provided.

        Args:
          router_db: A file or other object that can be iterated over in
            a line-by-line context.
        """
        imported = 0
        devices = {}
        for line in router_db:
            # Skip comment lines
            if line.strip().startswith('#'):
                continue
            match = self.re_router_db_line.match(line)
            if match is not None:
                device_name, device_type, status, _ = match.groups()
                if not self.ignore_down_devices:
                    # Anything other than up is down, so skip the device.
                    if not 'up' in status:
                        continue
                if device_type not in device_factory.VENDOR_MAP.keys():
                    logging.error('Invalid device type %r in router.db line: '
                                  '%r', device_type, line.replace('\n', ''))
                    logging.error('Device skipped. Valid device types are: %s',
                                  ', '.join(device_factory.VENDOR_MAP.keys()))
                    
                try:
                    addresses = self.address_lookup(device_name)
                except socket.gaierror:
                    # Devices without an address aren't cared about.
                    continue
                else:
                    devices[device_name] = DeviceInfo(
                        device_name=device_name, addresses=addresses,
                        device_type=device_type)
                    imported += 1
        self.devices.update(devices)
        self.ready = True
        return imported

    def scan(self):
        """Scans the root path for router.db files and loads them."""
        loaded = imported = 0
        for root, dirs, files in os.walk(self.root):
            # Skip CVS directories.
            if 'CVS' in dirs:
                dirs.remove('CVS')
            if 'router.db' in files:
                path = os.path.join(root, 'router.db')
                try:
                    router_db_file = open(path)
                    imported += self._read_router_db(router_db_file)
                    router_db_file.close()
                    loaded += 1
                except (IOError, OSError), e:
                    logging.error('Error occured reading %r. %s: %s', path,
                                  e.__class__.__name__, e[1])
                    continue
        logging.debug('%s imported %d router.db files [%d devices].',
                      self.__class__.__name__, loaded, imported)


class DeviceManager(object):
    """A class that polls, imports and exports device metadata in the system.

    Attributes:
      providers: A dict, string keyed provider name of DeviceProvider instances.
      config: A dict, the system configuration (e.g., via YAML import).
    """

    # TODO(afort): Set self.serve_ready to false every X minutes to update data.
    provider_classes = (RancidDeviceProvider, )
    config_section = 'device_sources'

    def __init__(self, config=None):
        self.providers = {}
        self.serve_ready = False
        if config:
            self.config = config
            logging.debug('Reading configuration for device manager')
            self.read_config()

    def add_providers(self, device_sources):
        """Adds providers from the configuration."""
        self.serve_ready = False
        if not device_sources:
            logging.error('No device source provider configuration.')
            return None

        for provider, kwargs in device_sources.iteritems():
            if 'provider' not in kwargs:
                logging.error(
                    'device_source named %r in config has no provider.',
                    provider)
                continue
            else:
                # Look for a valid provider and then load that instance.
                found = False
                for provider_class in self.__class__.provider_classes:
                    if provider_class.name == kwargs['provider'].lower():
                        found = True
                        priority = int(kwargs.get('priority', 100))
                        logging.debug('Adding %s source at priority %s',
                                     provider_class.__name__, priority)
                        self.providers[(priority, provider)] = provider_class(
                            **kwargs)
                        break
                if not found:
                    logging.error('Device source provider type %r unknown',
                                  kwargs['provider'])

    def provider(self, source):
        """Returns the provider object for the named device source.

        Args:
          source: A string, the device source name (from the configuration).

        Returns:
          A DeviceProvider subclass being the provider object, or None if
          no matching provider object was found.
        """
        for prio, source_name in self.providers:
            if source_name == source:
                return self.providers[(prio, source_name)]

    def read_config(self, config=None):
        config = config or self.config
        if config:
            self.add_providers(config.get(self.__class__.config_section))
        else:
            logging.error('No configuration found to load.')

    def scan_providers(self):
        """Scans all the providers to populate their indices."""
        if self.serve_ready:
            return
        for provider in self.providers.values():
            if not provider.ready:
                provider.scan()
        self.serve_ready = True

    def device_info(self, device_name):
        """Returns any known information about a single requested device.

        All device providers are consulted for the device information,
        lower priority number sources are preferred.

        Args:
          device_name: A string, the device name to return info for.

        Returns:
          A DeviceInfo namedtuple or;
          None if the device was not found.
        """
        self.scan_providers()
        for _, provider in sorted(self.providers.iteritems()):
            result = provider.device_info(device_name)
            if result is not None:
                return result

    def devices_matching(self, regexp):
        """Returns a set of device names matching the regexp.

        Args:
          regexp: A string, the regular expression to match against devices.

        Returns:
          A set of strings, device names that match the result.
        """
        self.scan_providers()
        if not regexp.startswith('^'):
            regexp = '^' + regexp
        if not regexp.endswith('$'):
            regexp += '$'
        result = set()
        for _, provider in sorted(self.providers.iteritems()):
            result |= provider.devices_matching(regexp)
        return result

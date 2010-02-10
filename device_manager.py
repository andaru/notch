#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Notch Device Manager.

The device manager manages device metadata for devices known to Notch.
It also provides an API for importing and exporting device metadata
from other sources, such as RANCID router.db files.

Without this subsystem, device vendor information would have to be submitted
by every client RPC.
"""

import adns
import ADNS
import yaml
import collections
import logging
import os
import re

import device_factory


# Information about a device, provided by the device_info
# pylint:disable-msg=C0103
DeviceInfo = collections.namedtuple('DeviceInfo',
                                    'device_name addresses device_type')


class DeviceProvider(object):
    """An abstract provider of device information."""

    # Override this in sub-classes.
    name = '__abstract__'
    # Stub this out for testing.
    dns_impl = ADNS.QueryEngine

    def __init__(self, **kwargs):
        """Use only keyword arguments in sub-class initialisers."""
        # Setup an adns querier.
        self._dns = self.__class__.dns_impl()

    def address_lookup(self, name):
        """Performs a synchronous DNS lookup for the requested address.

        Args:
          name: A string, a hostname to lookup in the DNS.

        Returns:
          A list of one or more IPv4 dotted-quad address strings.

        Raises:
          adns.Error: If there was an error during DNS lookup.
        """
        status, _, _, aliases = self._dns.synchronous(name, adns.rr.A)
        try:
            adns.exception(status)
        except adns.Error, exc:
            logging.debug('DNS lookup error: [%s] %s (query: %s)',
                          exc[0], exc[1], name)
            raise
        else:
            return aliases

    def scan(self):
        """Performs a scan over the source information.

        This method should set up any instance state required for the
        device_info callback to answer queries.
        """
        raise NotImplementedError

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


class RancidDeviceProvider(DeviceProvider):
    """A provider of devices sourced from RANCID router.db files.

    DNS is queried to populate the addresses properties in responses.
    """

    name = 'router.db'

    re_router_db_line = re.compile(r'([^:]+):([^:]+):([^:]+)?:?([^:]+?)?')

    def __init__(self, root=None, ignore_down_devices=False, **kwargs):
        super(RancidDeviceProvider, self).__init__(**kwargs)
        # DeviceInfo instances keyed by device name.
        self.devices = {}
        self.root = root
        self.ignore_down_devices = ignore_down_devices
        if root is None:
            raise ValueError('%s requires "root" keyword argument.'
                             % self.__class__.__name__)
        # Automatically scan the router.db files at startup.
        self.scan()

    def _read_router_db(self, router_db):
        """Reads the router.db file provided.

        Args:
          router_db: A file or other object that can be iterated over in
            a line-by-line context.
        """
        imported = 0
        for line in router_db:
            match = self.re_router_db_line.match(line)
            if match is not None:
                device_name, device_type, status, _ = match.groups()
                if not self.ignore_down_devices:
                    # Anything other than up is down, so skip the device.
                    if not 'up' in status:
                        continue
                try:
                    addresses = self.address_lookup(device_name)
                except adns.Error:
                    # Devices without an address aren't cared about.
                    continue
                else:
                    self.devices[device_name] = DeviceInfo(
                        device_name=device_name, addresses=addresses,
                        device_type=device_type)
                    imported += 1
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


class DnsTxtDeviceProvider(DeviceProvider):
    """A device provider that uses DNS TXT records to retrieve metadata."""

    name = 'dnstxt'

    RR_PREFIX = 'v=notch1'

    def __init__(self, keys=('device_type','connect_method',), **kwargs):
        super(DnsTxtDeviceProvider, self).__init__(**kwargs)
        self.keys = keys
        self.devices = {}

    def _consume_txt_rr(self, record):
        record = record.split()
        if record[0].lower() == RR_PREFIX:
            record = record[1:]
        else:
            raise StopIteration
        for kv in record:
            if ':' not in kv:
                continue
            k, v = kv.split(':', 1)
            if k in self.keys:
                yield k, v

    def device_info(self, device_name):
        # TODO(afort): Use a LRU-cache, instead of this simple memoisation.
        if device_name in self.devices:
            return self.devices[device_name]
        try:
            status, _, _, records = self._dns.synchronous(device_name,
                                                          adns.rr.TXT)
            adns.exception(status)
        except adns.Error, e:
            return None

        for record in records:
            if record.startswith(self.RR_PREFIX):
                kwargs = dict(
                    [(k, v) for (k, v) in self._consume_txt_rr(record)])
                if 'device_name' not in kwargs:
                    kwargs['device_name'] = device_name
                if 'addresses' not in kwargs:
                    addresses = self.address_lookup(device_name)
                    if addresses is None:
                        return None
                    kwargs['addresses'] = addresses
                self.devices[device_name] = DeviceInfo(
                    device_name=kwargs['device_name'],
                    addresses=kwargs['addresses'],
                    device_type=kwargs['device_type'])
                return self.devices[device_name]

    def scan(self):
        """This method uses live information only, so this method is a NOP."""
        pass


class DeviceManager(object):
    """A class that polls, imports and exports device metadata in the system.

    Attributes:
      providers: A dict, string keyed provider name of DeviceProvider instances.
      config: A dict, the system configuration (e.g., via YAML import).
    """

    # TODO(afort): Set self.serve_ready to false every X minutes to update data.

    provider_classes = (RancidDeviceProvider, DnsTxtDeviceProvider)
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
        if self.serve_ready:
            return
        for provider in self.providers.itervalues():
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

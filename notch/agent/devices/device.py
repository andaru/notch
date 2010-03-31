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

"""An abstract network element device model."""

import collections
import ipaddr
import logging

from notch.agent import errors


Timeouts = collections.namedtuple('Timeouts',
                                  'connect resp_short resp_long disconnect')


class Device(object):
    """An abstract network element or device.

    This class uses a semi-abstract delegate interface. Sub-classes
    generally implement the privately named methods (e.g., _connect) to
    supply device-specific functionality. This class handles common work.

    Attributes:
      addresses: A list of ipaddr.IP{V4|V6}Address object, the IP address(es).
      connected: A boolean, True if the device is connected to. (RO)
      connect_method: A string, the current connection method to use.
      name: A string, the device (host) name.
      vendor: A string, the device type name (e.g., 'juniper', 'cisco').
    """
    # In concrete classes, set this to the vendor OS identifier.
    vendor = None

    # Timeout values used by session to determine liveness/etc.
    # Override as required in concrete device classes.
    MAX_IDLE_TIME = 1800.0

    # Timeout values for various stages of the connection lifecycle.
    TIMEOUT_CONNECT = 30.0
    TIMEOUT_SMALL_RESPONSE = 4.0  # e.g., Prompts/menus.
    TIMEOUT_LARGE_RESPONSE = 180.0  # e.g., Full configs over a hosed 2meg link.
    TIMEOUT_DISCONNECT = 15.0

    def __init__(self, name=None, addresses=None):
        self._addresses = []
        try:
            self._set_addresses(addresses)
        except ipaddr.Error, e:
            logging.error('Error parsing addresses %s: %s',
                          addresses, str(e))
            self._addresses = []
        self.name = name
        self._connected = False
        self._connect_method = None

    def __eq__(self, other):
        return bool(self._addresses == other._addresses and
                    self.name == other.name and
                    self._connect_method == other._connect_method)

    def __str__(self):
        return ('%s(name=%r, addresses=%r, connected=%r, connect_method=%r, '
                'vendor=%r)' % (self.__class__.__name__,
                                self.name, self.addresses, self.connected,
                                self.connect_method, self.vendor))

    def _set_addresses(self, a):
        """Sets addresses suitable for the public property.

        Returns:
          A list, normally containing ipaddr.IPAddress objects.
          May also be a string, in which it is used to form a list.

        Raises:
          ipaddr.Error: An error occured creating the IPAddress object.
        """
        if a is None:
            self._addresses = []
            return
        if isinstance(a, str):
            self._addresses = [ipaddr.IPAddress(a)]
            return
        else:
            self._addresses = [ipaddr.IPAddress(address) for address in a]
            return

    def _set_connect_method(self, c):
        self._connect_method = c

    def connect(self, credential=None, connect_method=None):
        """Connects to the device."""
        if self.addresses is None or self.addresses == []:
            raise errors.DeviceWithoutAddressError
        if connect_method is not None:
            self._connect_method = connect_method
        # Try all of the available addresses.
        last_exc = None
        for address in self.addresses:
            try:
                self._connect(address=address, credential=credential)
                success = True
            except errors.ConnectError, e:
                success = False
                last_exc = e
                logging.error('Connect failed to %s on %s: [%s] %s',
                              self.name, address, e.__class__.__name__, str(e))
        if success:
            self._connected = True
        elif last_exc is not None:
            raise last_exc

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        """Sub-classes implement concrete connection method here."""
        raise NotImplementedError

    def disconnect(self):
        """Disconnects from the device."""
        self._disconnect()
        self._connected = False

    def _disconnect(self):
        """Sub-classes implement concrete disconnection method here."""
        raise NotImplementedError

    def command(self, command, mode=None):
        """Executes a command on the device."""
        raise NotImplementedError

    def get_config(self, source, mode=None):
        """Gets the configuration of the source in the desired mode."""
        raise NotImplementedError

    def set_config(self, destination, config_data, mode=None):
        """Sets the destination configuration with supplied data."""
        raise NotImplementedError

    def copy_file(self, source, destination, mode=None, overwrite=False):
        """Copies a file on the device's filesystem."""
        raise NotImplementedError

    def upload_file(self, source, destination, mode=None, overwrite=False):
        """Uploads a file to the device."""
        raise NotImplementedError

    def download_file(self, source, destination, mode=None, overwrite=False):
        """Downloads a file from the device."""
        raise NotImplementedError

    def delete_file(self, filename, mode=None):
        """Deletes a file from the device."""
        raise NotImplementedError

    def lock(self):
        """Locks the device against changes."""
        raise NotImplementedError

    def unlock(self):
        """Unlocks the device against changes."""
        raise NotImplementedError

    # Property attributes.
    addresses = property(lambda c: c._addresses, _set_addresses)
    connect_method = property(lambda c: c._connect_method, _set_connect_method)
    connected = property(lambda c: c._connected)
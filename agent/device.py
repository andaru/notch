#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""An abstract network element device model."""


import ipaddr
import logging

import errors


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

    def _set_addresses(self, a):
        """Sets addresses suitable for the public property.

        Returns:
          A list, normally containing ipaddr.IP*Address objects.

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
                logging.error('Error connecting to %s: %s', address, str(e))
        if success:
            self._connected = True
        elif last_exc:
            raise last_exc

    def _connect(self, address=None, connect_method=None, credential=None):
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

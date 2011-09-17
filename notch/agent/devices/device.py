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

import pexpect

import notch.agent.errors


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
      connect_methods: A tuple of strings, the currently supported
        connection methods.
      name: A string, the device (host) name.
      vendor: A string, the device type name (e.g., 'juniper', 'cisco').
    """
    # In concrete classes, set this to the vendor OS identifier.
    vendor = None

    # Default connect method for this device, e.g., 'sshv2' or 'telnet'
    DEFAULT_CONNECT_METHOD = None

    # Timeout values used by session to determine liveness/etc.
    # Override as required in concrete device classes.
    MAX_IDLE_TIME = 900.0

    # Timeout values for various stages of the connection lifecycle.
    TIMEOUT_CONNECT = 25.0  # Initial connection.
    TIMEOUT_RESP_SHORT = 12.0  # e.g., Prompts/menus.
    TIMEOUT_RESP_LONG = 180.0  # e.g., Full configs over a hosed 2meg link.
    TIMEOUT_DISCONNECT = 10.0

    # Devices will not attempt reconnection after experiencing these errors.
    # socket.error:
    #   errno 101: Network is unreachable.
    #   errno 111: Connection refused.
    #   errno 113: No route to host.
    DONT_RETRY_ERRNO = (101, 111, 113, )

    def __init__(self, name=None, addresses=None):
        self._addresses = []
        self.connect_methods = tuple()
        try:
            self._set_addresses(addresses)
        except (ValueError, TypeError), e:
            logging.error('Error parsing addresses %s: %s',
                          addresses, str(e))
            self._addresses = []

        self.name = name
        self._connected = False
        self._connect_method = None
        self._current_credential = None

        self.timeouts = Timeouts(connect=self.TIMEOUT_CONNECT,
                                 resp_short=self.TIMEOUT_RESP_SHORT,
                                 resp_long=self.TIMEOUT_RESP_LONG,
                                 disconnect=self.TIMEOUT_DISCONNECT)

    def __eq__(self, other):
        return bool(self._addresses == other._addresses and
                    self.name == other.name)

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
        elif isinstance(a, str):
            self._addresses = [ipaddr.IPAddress(a)]
        else:
            self._addresses = [ipaddr.IPAddress(address) for address in a]

    def _set_connect_method(self, c):
        self._connect_method = c

    def connect(self, credential=None, connect_method=None):
        """Connects to the device."""
        if self.addresses is None or self.addresses == []:
            raise notch.agent.errors.DeviceWithoutAddressError(self.name)
        # Only change the connect_method if the requested value is valid
        # on this device. If all else fails, use the device model default.
        if connect_method in self.connect_methods:
            self._connect_method = connect_method
        if self._connect_method is None:
            self._connect_method = self.DEFAULT_CONNECT_METHOD
        self._current_credential = credential

        logging.debug('CONNECT %s %s', self.name, self._connect_method)
        # Try all of the available addresses.
        last_exc = None
        success = False
        for address in self.addresses:
            try:
                self._connect(address=address, credential=credential,
                              connect_method=self._connect_method)
                success = True
                logging.debug('CONNECT_OK %s %s @ %s',
                              self.name, self._connect_method, address)
                break
            except (EOFError, pexpect.EOF, pexpect.TIMEOUT, OSError), e:
                success = False
                # Don't retry certain errors: futility is not a strategy.
                last_exc = notch.agent.errors.ConnectError(str(e))
                if hasattr(e, 'errno') and e.errno not in self.DONT_RETRY_ERRNO:
                    last_exc.retry = True
                elif isinstance(e, pexpect.EOF):
                    last_exc.retry = True
                logging.error('CONNECT_FAIL %s %s @ %s: [%s] %s',
                              self.name, self._connect_method, address,
                              e.__class__.__name__, str(e))
            except notch.agent.errors.ConnectError, e:
                success = False
                last_exc = e
                logging.error('CONNECT_FAIL %s %s @ %s: [%s] %s',
                              self.name, self._connect_method, address,
                              e.__class__.__name__, str(e))
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
        logging.debug('DISCONNECT %s %s', self.name, self._connect_method)
        self._disconnect()
        self._connected = False

    def _disconnect(self):
        """Sub-classes implement concrete disconnection method here."""
        raise NotImplementedError

    def _command(self, command, mode=None):
        """Implements the execution of a command on the device."""
        raise NotImplementedError

    def command(self, command, mode=None):
        """Executes a command on the device."""
        return self._command(command, mode=mode)

    def get_config(self, source, mode=None):
        """Gets the configuration of the source in the desired mode."""
        raise NotImplementedError

    def set_config(self, destination, config_data, mode=None):
        """Sets the destination configuration with supplied data."""
        _ = destination, config_data, mode
        raise NotImplementedError

    def copy_file(self, source, destination, mode=None, overwrite=False):
        """Copies a file on the device's filesystem."""
        _ = source, destination, mode, overwrite
        raise NotImplementedError

    def upload_file(self, source, destination, mode=None, overwrite=False):
        """Uploads a file to the device."""
        _ = source, destination, mode, overwrite
        raise NotImplementedError

    def download_file(self, source, destination, mode=None, overwrite=False):
        """Downloads a file from the device."""
        _ = source, destination, mode, overwrite
        raise NotImplementedError

    def delete_file(self, filename, mode=None):
        """Deletes a file from the device."""
        _ = filename, mode
        raise NotImplementedError

    def lock(self):
        """Locks the device against changes."""
        raise NotImplementedError

    def unlock(self):
        """Unlocks the device against changes."""
        raise NotImplementedError

    # Property attributes.
    addresses = property(lambda self: self._addresses, _set_addresses)
    connect_method = property(lambda self: self._connect_method,
                              _set_connect_method)
    connected = property(lambda self: self._connected)

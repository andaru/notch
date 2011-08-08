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

"""The Notch Session model.

A Session models the relationship between a particular common set of
request attributes (known as the session key) and a device connection.

This connection may be idle, disconnected, connected, or active.
The controller manages a cache of Session object instances,
keeping devices connected until idle timers expire.
"""

import base64
import collections
import logging
import threading
import time

import errors


# Used to uniquely identify a session.
SessionKey = collections.namedtuple(
    'SessionKey', 'device_name connect_method user privilege_level')


class Session(object):
    """A session manages a connections and requests to a device."""

    # Methods supported by the Device API that may be requested.
    valid_requests = ('command', 'get_config', 'set_config',
                      'copy_file', 'upload_file', 'download_file',
                      'delete_file', 'lock', 'unlock')

    def __init__(self, device=None):
        # TODO(afort): Allow devices to have multiple authentication
        # credentials available (e.g., during password changes).
        self._exclusive = threading.Lock()

        self.device = device
        self._credential = None

        self._connected = False
        self.idle = True

        self.time_last_connect = None
        self.time_last_disconnect = None
        self.time_last_response = None
        self.time_last_request = None

        self._bytes_sent = 0
        self._bytes_recv = 0

        self._errors_connect = 0
        self._errors_disconnect = 0

    def __eq__(self, other):
        """Returns True if the other session manages the same device."""
        return bool(self.device == other.device)

    def __str__(self):
        if self.device:
            hostname = 'on %s' % self.device.name
        else:
            hostname = '(not connected)'

        if self._credential:
            username = ' username=%s' % self._credential.username
        else:
            username = ''

        return '<%s %s%s>' % (self.__class__.__name__, hostname, username)

    @property
    def connected(self):
        return self._connected

    def _credential(self):
        return self._credential

    def _set_credential(self, c):
        """Sets the session credential, reconnecting if presently connected."""
        try_to_reconnect = self._connected
        if c != self._credential:
            try:
                self.disconnect()
            except errors.Error, e:
                # Disconnection failed, update the cred and reconnect anyway.
                logging.error(str(e))
        self._credential = c

        if try_to_reconnect:
            try:
                self.connect()
            except errors.ConnectError:
                # If we aren'table to reconnect, it's no great loss.
                pass

    credential = property(_credential, _set_credential)

    def connect(self):
        """Connects the session using the current Credential."""
        if self.device is None:
            return
        elif self._connected:
            return
        if self._credential is None:
            raise errors.NoMatchingCredentialError()

        self.device.connect(credential=self._credential,
                            connect_method=self._credential.connect_method)
        self.time_last_connect = time.time()
        self._connected = True
        self.idle = True

    def disconnect(self):
        """Disconnects the session."""
        if self.device is None:
            return
        elif not self._connected:
            return
        self.device.disconnect()
        self.time_last_disconnect = time.time()
        self._connected = False
        self.idle = True

    def request(self, method, *args, **kwargs):
        """Executes a request on this session."""
        result = None
        logging.debug('Acquiring lock for %s', self)
        self._exclusive.acquire()
        try:
            logging.debug('Acquired lock for %s', self)
            # Check the method name is valid.
            if not method in self.valid_requests:
                raise errors.InvalidRequestError(
                    'Method %r not part of the device API.' % method)
            if self.device is None:
                raise errors.InvalidDeviceError('Device not yet initialised.')
            if not self._connected:
                self.connect()
            # Execute the method.
            self.time_last_request = time.time()
            device_method = getattr(self.device, method)

            self.idle = False
            try:
                # Remove the device_name argument not used in device.py.
                # TODO(afort): device.py/subclasses to take **kwargs instead?
                if 'device_name' in kwargs:
                    del kwargs['device_name']
                try:
                    # May raise any exception, we'll trigger a retry
                    # upon API errors with the retry attribute set.
                    result = device_method(*args, **kwargs)
                    # We must now base64 encode the string result,
                    # incase it contains binary data.

                except errors.ApiError, e:
                    # Normally, we'll disconnect upon error just incase.
                    if e.disconnect_on_error:
                        logging.debug(
                            'Disconnecting session %s (error occured).', self)
                        self.disconnect()
                    # Single optional retry.
                    if e.retry:
                        logging.debug('Retrying request on session %s.', self)
                        self.connect()
                        result = device_method(*args, **kwargs)
                    else:
                        raise e
                self.time_last_response = time.time()
            finally:
                self.idle = True

        finally:
            logging.debug('Releasing lock for %s', self)
            self._exclusive.release()

        try:
            return base64.b64encode(result)
        except Exception, e:
            logging.error('Error base64 encoding result. '
                          '%s: %s. Original result: %r',
                          e.__class__.__name__, str(e), result)
            return result



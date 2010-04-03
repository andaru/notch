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

"""Telnet device transport via telnetlib."""


import re
import telnetlib

from eventlet.green import socket

from notch.agent import errors


class Error(Exception):
    pass


class SendError(Error):
    pass


DEFAULT_RETRIES = 3

class TelnetDeviceTransport(object):
    """Telnet device transport via telnetlib.

    Attributes:
      address: A string hostname or IPAddr object.
      port: An int, the TCP port to connect to. None uses the default port.
      timeouts: A device.Timeouts namedtuple, timeout values to use.
    """

    DEFAULT_PORT = 23
    DEFAULT_TIMEOUT_CONNECT = 30
    DEFAULT_TIMEOUT_RESP_SHORT = 7
    DEFAULT_TIMEOUT_RESP_LONG = 180
    DEFAULT_TIMEOUT_DISCONNECT = 15
    
    def __init__(self, address=None, port=None, timeouts=None, **kwargs):
        """Initializer.

        Args:
          address: A string hostname or IPAddr object.
          port: An int, the TCP port to connect to. None uses the default port.
          timeouts: A device.Timeouts namedtuple, timeout values to use.
        """
        _ = kwargs
        self.address = address
        self.timeouts = timeouts
        self.port = port or self.DEFAULT_PORT
        self._c = None

    def connect(self):
        if self.timeouts:
            timeout = self.timeouts.connect or self.DEFAULT_TIMEOUT_CONNECT
        else:
            timeout = self.DEFAULT_TIMEOUT_CONNECT
        try:
            self._c = telnetlib.Telnet(str(self.address), self.port, timeout)
        except socket.error, e:
            raise errors.ConnectError('Error connecting to %s. %s: %s'
                                      % (str(self.address),
                                         e.__class__.__name__, str(e)))

    def flush(self):
        """Eagerly flush any remaining data from the read fd."""
        if self._c is None:
            return
        else:
            return self._c.read_very_eager()

    def _close(self):
        if self._c is None:
            return
        else:
            self._c.close()
            self._c = None

    def disconnect(self):
       """Closes the telnet session and returns any remaining data."""
       result = None
       try:
           try:
               result = self.flush()
           except EOFError:
               pass
       finally:
           try:
               self._close()
               return result
           except EOFError:
               pass

    def write(self, s):
        try:
            self._c.write(s)
        except (socket.error, EOFError), e:
            raise errors.CommandError('%s: %s' % (e.__class__.__name__, str(e)))

    def expect(self, re_list, timeout=None):
        if self.timeouts:
            timeout = self.timeouts.resp_long or self.DEFAULT_TIMEOUT_RESP_LONG
        else:
            timeout = self.DEFAULT_TIMEOUT_RESP_LONG
        return self._c.expect(re_list, timeout=timeout)       

    def command(self, command, prompt, timeout=None):
        """Executes the command, returning any data prior to the prompt."""
        if self.timeouts:
            timeout_long = timeout or self.timeouts.resp_long
            timeout_short = timeout or self.timeouts.resp_short
        else:
            timeout_long = self.DEFAULT_TIMEOUT_RESP_LONG
            timeout_short = self.DEFAULT_TIMEOUT_RESP_SHORT
        self.write('\n')
        i, matchobj, pretext = self.expect([prompt], timeout_short)
        if i == - 1:
            raise errors.CommandError(
                'Device in an unknown state, cannot continue.')

        self.write(command + '\n')
        # Expect the command to be echoed back first.
        i, matchobj, pretext = self.expect(
            [re.escape(command) + '\r\n'], timeout_short)
        if i == -1:
            raise errors.CommandError(
                'Device did not start response within short response timeout.')

        i, matchobj, pretext = self.expect([prompt], timeout_long)
        if i == -1:
            raise errors.CommandError('Prompt not found after command.')
        else:
            prompt_index = pretext.rfind(prompt)
            if prompt_index == -1:
                return pretext
            else:
                return pretext[:prompt_index]


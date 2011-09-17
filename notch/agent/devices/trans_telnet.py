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

import logging
import telnetlib

import fdpexpect

import socket

import notch.agent.errors

import trans


class Error(Exception):
    pass


class SendError(Error):
    pass


class TelnetDeviceTransport(trans.DeviceTransport):
    """Telnet device transport via telnetlib.

    Attributes:
      address: A string hostname or IPAddr object.
      port: An int, the TCP port to connect to. None uses the default port.
      timeouts: A device.Timeouts namedtuple, timeout values to use.
    """

    DEFAULT_PORT = 23

    @property
    def match(self):
        if self._expect:
            return self._expect.match

    @property
    def before(self):
        if self._expect:
            return self._expect.before

    @property
    def after(self):
        if self._expect:
            return self._expect.after

    def connect(self, unused_credential):
        timeout = self.timeouts.connect
        try:
            self._c = telnetlib.Telnet(str(self.address), self.port, timeout)
            self._expect = fdpexpect.fdspawn(self._c.fileno())
        except socket.error, e:
            raise notch.agent.errors.ConnectError(
                'Error connecting to %s. %s: %s'
                % (str(self.address), e.__class__.__name__, str(e)))

    def flush(self):
        """Eagerly flush any remaining data from the read fd."""
        if self._c is None:
            return
        else:
            return self._c.read_very_eager()

    def _close(self):
        if self._c is not None:
            self._c.close()
            self._c = None

    def disconnect(self):
       """Closes the telnet session and returns any remaining data."""
       try:
           self._close()
       except EOFError:
           logging.debug('trans_telnet [%s:%s] EOFError during disconnect()',
                         self.address, self.port)

    def write(self, s):
        try:
            self._expect.send(s)
        except (socket.error, EOFError), e:
            raise notch.agent.errors.CommandError(
                '%s: %s' % (e.__class__.__name__, str(e)))
        except OSError, e:
            exc = notch.agent.errors.CommandError('OSError: %s' % str(e))
            exc.retry = True
            raise exc

    def expect(self, re_list, timeout=None):
        timeout = timeout or self.timeouts.resp_long
        return self._expect.expect(re_list, timeout=timeout)

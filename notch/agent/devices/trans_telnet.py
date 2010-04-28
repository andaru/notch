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

import fdpexpect
import pexpect

from eventlet.green import socket

import notch.agent.errors


class Error(Exception):
    pass


class SendError(Error):
    pass


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

    def command(self, command, prompt, timeout=None, expect_trailer='\r\n',
                command_trailer='\n', expect_command=True):
        """Executes the command.

        This returns any data after the CLI command sent, prior to the
        CLI prompt after the output ceases.
        """
        timeout_long = timeout or self.timeouts.resp_long
        timeout_short = timeout or self.timeouts.resp_short

        # Find the prompt and flush the expect buffer.
        self.write(command_trailer)
        if isinstance(prompt, str):
            esc_prompt = re.escape(prompt)
        else:
            esc_prompt = prompt
        i = self.expect([esc_prompt, pexpect.EOF, pexpect.TIMEOUT],
                        timeout_short)
        if i == 1:
            exc = notch.agent.errors.CommandError(
                'EOF received during command %r' % command)
            exc.retry = True
            raise exc
        elif i == 2:
            raise notch.agent.errors.CommandError('CLI prompt not found prior '
                                                  'to sending command.')

        # Send the command.
        self.write(command + command_trailer)

        # Expect the command to be echoed back first, perhaps. If the
        # device echoes back the 'full' command for an abbreviated
        # command input (um, thanks), allow for that, also.
        if expect_command:
            i = self.expect(
                [re.escape(command) + expect_trailer, pexpect.EOF,
                 pexpect.TIMEOUT], timeout_short)
        else:
            trailer = expect_trailer or os.linesep
            i = self.expect([trailer, pexpect.EOF, pexpect.TIMEOUT],
                            timeout_short)
        if i > 0:
            exc = notch.agent.errors.CommandError(
                'Device did not start response within short response timeout.')
            exc.retry = True
            raise exc

        i = self.expect([esc_prompt, pexpect.EOF, pexpect.TIMEOUT],
                        timeout_long)
        if i == 1:
            exc = notch.agent.errors.CommandError(
                'EOF received during command %r' % command)
            exc.retry = True
            raise exc
        elif i == 2:
            # Don't retry timeouts on the whole command - they usually
            # indicate overloaded devices.
            raise notch.agent.errors.CommandError(
                'Command executed, CLI prompt not seen after %.1f sec' %
                timeout_long)
        else:
            # Clean up the output to include only the part between the first
            # character after the newline after the command requested until
            # the last character prior to the next CLI prompt.
            prompt_index = self.before.rfind(prompt)
            if prompt_index == -1:
                return self.before
            else:
                return self.before[:prompt_index]

    def ___command(self, command, prompt, timeout=None):
        """Executes the command, returning any data prior to the prompt."""
        if self.timeouts:
            timeout_long = timeout or self.timeouts.resp_long
            timeout_short = timeout or self.timeouts.resp_short
        else:
            timeout_long = self.DEFAULT_TIMEOUT_RESP_LONG
            timeout_short = self.DEFAULT_TIMEOUT_RESP_SHORT
        self.write('\n')
        i = self.expect([re.escape(prompt)], timeout_short)
        if i != 0:
            raise notch.agent.errors.CommandError(
                'Device in an unknown state, cannot continue.')

        self.write(command + '\n')
        # Expect the command to be echoed back first.
        i = self.expect(
            [re.escape(command)], timeout_short)
        if i != 0:
            raise notch.agent.errors.CommandError(
                'Device did not start response within short response timeout.')

        i = self.expect([re.escape(prompt), pexpect.TIMEOUT, pexpect.EOF],
                        timeout_long)
        if i != 0:
            raise notch.agent.errors.CommandError(
                'Prompt not found after command.')
        else:
            prompt_index = self.before.rfind(prompt)
            if prompt_index == -1:
                return self.before
            else:
                return self.before[:prompt_index]


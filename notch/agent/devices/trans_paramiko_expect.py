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

from eventlet.green import socket

import paramiko

import notch.agent.errors

import paramiko_expect


# Constants
DEFAULT_RECV_SIZE = 4096
DEFAULT_PORT = 22


class Error(Exception):
    pass


class SendError(Error):
    pass


class ParamikoExpectTransport(object):
    """SSH2 with expect, via Paramiko.

    Attributes:
      address: A string hostname or IPAddr object.
      port: An int, the TCP port to connect to. None uses the default port.
      timeouts: A device.Timeouts namedtuple, timeout values to use.
    """
    
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
        self.port = 22
        self._c = paramiko_expect.ParamikoSpawn(None)

    @property
    def match(self):
        if self._c:
            return self._c.match

    @property
    def before(self):
        if self._c:
            return self._c.before

    @property
    def after(self):
        if self._c:
            return self._c.after

    def connect(self, credential):
        timeout = self.timeouts.connect
        if credential.ssh_private_key is not None:
            pkey = paramiko.PKey.from_private_key(
                credential.ssh_private_key_file)
        else:
            pkey = None
        self._ssh_client = paramiko.SSHClient()

        # TODO(afort): Be more secure.
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            print self.port

            self._ssh_client.connect(self.address,
                                     port=self.port,
                                     username=credential.username,
                                     password=credential.password,
                                     pkey=pkey,
                                     timeout=self.timeouts.connect)
            # Connect paramiko to pexpect.
            if self._c is None:
                self._c = paramiko_expect.ParamikoSpawn(None)
            self._c.channel = self._ssh_client.invoke_shell()
        except (paramiko.ssh_exception.SSHException, socket.error), e:
            if e.args[1] == 'EADDRNOTAVAIL':
                raise notch.agent.errors.ConnectError(
                    'Port %s on %r is closed.' % (self.port, self.address))
            else:
                raise notch.agent.errors.ConnectError(str(e))

    def flush(self):
        """Eagerly flush any remaining data from the read fd."""
        if self._c is None:
            return
        else:
            return self._c.read_nonblocking(size=DEFAULT_RECV_SIZE)

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
            self._c.send(s)
        except (socket.error, EOFError), e:
            raise notch.agent.errors.CommandError(
                '%s: %s' % (e.__class__.__name__, str(e)))

    def expect(self, re_list, timeout=None):
        if timeout is None and self.timeouts:
            timeout = self.timeouts.resp_long
        return self._c.expect(re_list, timeout=timeout)

    def command(self, command, prompt, timeout=None, expect_trailer='\r\n',
                command_trailer='\n', expect_command=True):
        """Executes the command, returning any data prior to the prompt."""
        timeout_long = timeout or self.timeouts.resp_long
        timeout_short = timeout or self.timeouts.resp_short
        self.write(command_trailer)
        if isinstance(prompt, str):
            esc_prompt = re.escape(prompt)
        else:
            esc_prompt = prompt
        i = self.expect([esc_prompt], timeout_short)
        if i == - 1:
            raise notch.agent.errors.CommandError(
                'Device in an unknown state, cannot continue.')
        self.write(command + command_trailer)

        # Expect the command to be echoed back first, perhaps.
        # If the device echoes back the 'full' command for the
        # abbreviated command entered, this should be disabled.
        if expect_command:
            i = self.expect(
                [re.escape(command) + expect_trailer], timeout_short)
        else:
            i = self.expect([expect_trailer], timeout_short)
        if i == -1:
            raise notch.agent.errors.CommandError(
                'Device did not start response within short response timeout.')
        i = self.expect([esc_prompt], timeout_long)
        if i == -1:
            raise notch.agent.errors.CommandError(
                'Prompt not found after command %r.' % command)
        else:
            prompt_index = self._c.before.rfind(prompt)
            if prompt_index == -1:
                return self._c.before
            else:
                return self._c.before[:prompt_index]

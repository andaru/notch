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


import os
import re

from eventlet.green import socket

import paramiko
import pexpect

import notch.agent.errors

import paramiko_expect
import scp

import trans

# Constants
DEFAULT_RECV_SIZE = 4096
DEFAULT_PORT = 22


class Error(Exception):
    pass


class SendError(Error):
    pass


class ParamikoExpectTransport(trans.DeviceTransport):
    """SSH2 with expect, via Paramiko.

    Attributes:
      address: A string hostname or IPAddr object.
      port: An int, the TCP port to connect to. None uses the default port.
      timeouts: A device.Timeouts namedtuple, timeout values to use.
    """

    def __init__(self, address=None, port=None, timeouts=None,
                 strip_ansi=False, **kwargs):
        """Initializer.

        Args:
          address: A string hostname or IPAddr object.
          port: An int, the TCP port to connect to. None uses the default port.
          timeouts: A device.Timeouts namedtuple, timeout values to use.
          strip_ansi: A boolean, if True, strip ANSI escape sequences.
        """
        _ = kwargs
        self.address = address
        self.timeouts = timeouts
        self.port = 22
        self.strip_ansi = strip_ansi
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
        except socket.timeout, e:
            raise notch.agent.errors.ConnectError('Timed out after %.1fs' %
                                                  self.timeouts.connect)
        except (paramiko.ssh_exception.SSHException, socket.error), e:
            try:
                if e.args[1] == 'EADDRNOTAVAIL':
                    raise notch.agent.errors.ConnectError(
                        'Port %s on %r is closed.' % (self.port, self.address))
                else:
                    raise notch.agent.errors.ConnectError(str(e))
            except IndexError, unused_e:
                self.disconnect()
                self._ssh_client = None
                # Raise the message from the original exception.
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
       """Closes the SSH session and returns any remaining data."""
       result = None
       try:
           try:
               result = self.flush()
               self._close()
           except Exception, e:
                logging.error('Transport close error: %s: %s',
                              e.__class__.__name__, str(e))
                pass
       finally:
           return result

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

    def ___command(self, command, prompt, timeout=None, expect_trailer='\r\n',
                command_trailer='\n', expect_command=True,
                pager=None, pager_response=' '):
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
                                                  'to sending command %r.'
                                                  % command)

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
            prompt_index = self._c.before.rfind(prompt)
            if prompt_index == -1:
                return self._c.before
            else:
                return self._c.before[:prompt_index]

    def download_and_return_file(self, source):
        try:
            scp_client = scp.ScpClient(self._c.transport)
            local_file = tempfile.TemporaryFile()
            scp_client.get(source, local_file)
        except Exception:
            raise notch.agent.errors.DownloadFile
        return local_file.read()

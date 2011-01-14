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

    def download_and_return_file(self, source):
        try:
            scp_client = scp.ScpClient(self._c.transport)
            local_file = tempfile.TemporaryFile()
            scp_client.get(source, local_file)
        except Exception:
            raise notch.agent.errors.DownloadFile
        return local_file.read()

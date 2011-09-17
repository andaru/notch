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

"""SSH connection transport via pexpect and command-line SSH."""

import logging
import socket

import pexpect

import notch.agent.errors
import trans


class Error(Exception):
    pass


class SendError(Error):
    pass


class SshDeviceTransport(trans.DeviceTransport):
    """SSHv1 device transport via command-line SSH.

    Attributes:
      address: A string hostname or IPAddr object.
      port: An int, the TCP port to connect to. None uses the default port.
      timeouts: A device.Timeouts namedtuple, timeout values to use.
    """

    DEFAULT_PORT = 22

    @property
    def match(self):
        if self._expect.isalive():
            return self._expect.match

    @property
    def before(self):
        if self._expect.isalive():
            return self._expect.before

    @property
    def after(self):
        if self._expect.isalive():
            return self._expect.after

    def connect(self, credential):
        ssh_cmd = ['ssh -tt',
                   '-1',
                   '-p%s' % self.port,
                   '-l%s' % credential.username,
                   '-oUserKnownHostsFile=/dev/null',
                   '-oStrictHostKeyChecking=no',
                   ]
        # Are we using pubkey authentication or not?
        if credential.ssh_private_key_filename:
            ssh_cmd.append('-i%s' % credential.ssh_private_key_filename)
        else:
            ssh_cmd.extend([
                '-oRSAAuthentication=no',
                '-oPubkeyAuthentication=no',
                ])
        ssh_cmd.append(self.address)
        try:
            self._expect = pexpect.spawn(' '.join(ssh_cmd),
                                         timeout=self.timeouts.connect)
        except (socket.error, TypeError, pexpect.ExceptionPexpect), e:
            raise notch.agent.errors.ConnectError(
                'Error connecting to %s. %s: %s'
                % (str(self.address), e.__class__.__name__, str(e)))

    def flush(self):
        """Flush any remaining data."""
        if self._expect is None:
            return
        else:
            return self._expect.flush()

    def _close(self):
        if self._expect is not None:
            self._expect.close(force=True)
            self._expect = None

    def disconnect(self):
       """Closes the telnet session and returns any remaining data."""
       try:
           self._close()
       except (socket.error, TypeError, EOFError, pexpect.ExceptionPexpect):
           logging.debug('trans_telnet [%s:%s] EOFError during disconnect()',
                         self.address, self.port)

    def write(self, s):
        try:
            self._expect.send(s)
        except (socket.error, EOFError, pexpect.ExceptionPexpect), e:
            raise notch.agent.errors.CommandError(
                '%s: %s' % (e.__class__.__name__, str(e)))
        except OSError, e:
            exc = notch.agent.errors.CommandError('OSError: %s' % str(e))
            exc.retry = True
            raise exc

    def expect(self, re_list, timeout=None):
        timeout = timeout or self.timeouts.resp_long
        return self._expect.expect(re_list, timeout=timeout)

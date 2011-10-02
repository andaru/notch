#!/usr/bin/env python
#
# Copyright 2011 Andrew Fort. All Rights Reserved.
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

"""Notch device model for Force 10 Networks FTOS devices.

This is largely an IOS look-alike, though it does not support paramiko-style
SSH, so we play expect with it.
"""

import logging

import pexpect

import dev_ios

import trans_ssh
import trans_telnet

import notch.agent.errors


class FtosDevice(dev_ios.IosDevice):
    """Force 10 Networks FTOS style device model.

    Connect methods supported:
      sshv1 (via command-line SSH in interactive mode with pexpect)
      telnet (via telnetlib)
    """

    DEFAULT_CONNECT_METHOD = 'sshv1'

    def __init__(self, name=None, addresses=None):
        super(FtosDevice, self).__init__(name=name, addresses=addresses)
        self._ssh_client = None
        self.connect_methods = ('telnet', 'sshv1')
        # Not used directly.
        self._port = None

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        port = port or self._port
        connect_method = connect_method or self.connect_method
        if connect_method == 'sshv1' or connect_method is None:
            self._transport = trans_ssh.SshDeviceTransport(
                timeouts=self.timeouts, port=port, address=str(address),
                command_trailer='\r\n')
        elif connect_method == 'telnet':
            self._transport = trans_telnet.TelnetDeviceTransport(
                timeouts=self.timeouts, port=port, address=str(address),
                command_trailer='\r\n')
        else:
            raise ValueError('Unsupported connect_method: %r' %
                             connect_method)
        # May raise notch.agent.errors.ConnectError
        self._transport.connect(credential)
        self._login(credential.username, credential.password,
                    connect_method=connect_method)
        if credential.enable_password is not None and credential.auto_enable:
            self._enable(credential.enable_password)
        self._disable_pager()

    def _login(self, username, password, connect_method=None):
        connect_method = connect_method or self.connect_method
        if connect_method == 'sshv1':
            i = self._transport.expect(
                [self.PASSWORD_PROMPT, self.PROMPT, pexpect.TIMEOUT,
                 pexpect.EOF], self.timeouts.resp_short)
            if i > 1:
                raise notch.agent.errors.ConnectError(
                    'Did not find password prompt %r.'
                    % self.PASSWORD_PROMPT)
            elif i == 1:
                logging.debug('Logged in to %r. %s', self.name, str(self._transport._expect))
            else:
                self._transport.write(password + '\n')
                i = self._transport.expect(
                    [self.PROMPT, pexpect.TIMEOUT, pexpect.EOF],
                    self.timeouts.resp_short)
                if not i:
                    logging.debug('Logged in to %r.', self.name)
                    self._prompt = self._transport.match.group(0)
                    logging.debug('Expected prompt is now: %r', self._prompt)
                else:
                    raise notch.agent.errors.ConnectError(
                        'Password not accepted on %r.' % self.name)
        else:
            super(FtosDevice, self)._login(username, password,
                                           connect_method=connect_method)

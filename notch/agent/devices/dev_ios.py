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

"""Notch device model for cisco IOS 'style' operating systems.

There's a surprising number of near look-alikes of IOS interfaces,
and this module will deal with many of them.
"""


import logging
import re
from eventlet.green import socket

import paramiko
import pexpect

import notch.agent.errors

import device
import trans_paramiko_expect
import trans_telnet


CTRL_Z = r'\x16'


class EnableFailedError(Exception):
    pass


class IosDevice(device.Device):
    """cisco IOS style device model.

    Connect methods supported:
      sshv2 (via Paramiko in interactive mode with pexpect)
      telnet (via telnetlib)
    """

    LOGIN_PROMPT = 'Username: '
    PASSWORD_PROMPT = 'Password: '
    PROMPT = re.compile(r'\S+\s?[>#]')
    ERR_NOT_SETUP = 'Password required, but none set'

    def __init__(self, name=None, addresses=None):
        super(IosDevice, self).__init__(name=name, addresses=addresses)
        self._ssh_client = None
        # Not used directly.
        self._port = None

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        connect_method = connect_method or self.connect_method
        if connect_method == 'sshv2':
            self._transport = trans_paramiko_expect.ParamikoExpectTransport(
                timeouts=self.timeouts)
        elif connect_method == 'telnet' or connect_method is None:
            self._transport = trans_telnet.TelnetDeviceTransport(
                timeouts=self.timeouts)
        else:
            raise ValueError('Unsupported connect_method: %r' %
                             connect_method)
        self._transport.address = str(address)
        if port:
            self._transport.port = port
        # May raise notch.agent.errors.ConnectError
        self._transport.connect(credential)
        self._login(credential.username, credential.password)
        self._get_prompt()
        # TODO(afort): Add .autoenable to the credential record.
        if credential.enable_password:
            logging.debug('Enabling on %r' % self.name)
            self._enable(credential.enable_password)
        self._disable_pager()

    def _get_prompt(self):
        self._transport.write('\n')
        i = self._transport.expect([self.PROMPT], 0.0)
        if i == 0:
            self._prompt = self._transport.match.group(0)
            logging.debug('Expected prompt is now: %r', self._prompt)
            return
        else:
            logging.error('Failed to get prompt on %s', self.name)

    def _enable(self, enable_password):
        self._transport.write('enable\n')
        while True:
            i = self._transport.expect([r'Password:',
                                        r'timeout expired',
                                        r'% Bad secrets',
                                        self.PROMPT,
                                        pexpect.TIMEOUT,
                                        pexpect.EOF,
                                        ], 10)
            if i == 0 or i == 1:
                self._transport.write(enable_password + '\n')
                continue
            elif i == 2:
                raise notch.agent.errors.AuthenticationError(
                    'Enable authentication failed.')
            elif i == 3:
                logging.debug('Enabled on %s', self.name)
                # The prompt will change when we enable.
                self._prompt = self._transport.match.group(0)
                logging.debug('Prompt is now: %r', self._prompt)
                return
            else:
                raise notch.agent.errors.EnableError(
                    'Failed to enable on %r.' % self.name)

    def _login(self, username, password):
        if self.connect_method == 'telnet' or self.connect_method is None:
            self._transport.write('\n')
            i = self._transport.expect(
                [self.LOGIN_PROMPT, self.ERR_NOT_SETUP, pexpect.TIMEOUT,
                 pexpect.EOF], self.timeouts.resp_short)
            if i > 1:
                # Didn't see anything we expected.
                raise notch.agent.errors.ConnectError(
                    'Did not find login prompt %r.' % self.LOGIN_PROMPT)
            elif i == 1:
                pretext = pretext.lstrip()
                raise notch.agent.errors.ConnectError(
                    'Device says: %r' % pretext)
            else:
                self._transport.write(username + '\n')
                i = self._transport.expect(
                    [self.PASSWORD_PROMPT, pexpect.TIMEOUT,
                     pexpect.EOF], self.timeouts.resp_short)
                if i != 0:
                    raise notch.agent.errors.ConnectError(
                        'Did not find password prompt %r.'
                        % self.PASSWORD_PROMPT)
                else:
                    self._transport.write(password + '\n')
                    i = self._transport.expect(
                        [self.PROMPT, pexpect.TIMEOUT, pexpect.EOF],
                        self.timeouts.resp_short)                    
                    if i == 0:
                        logging.debug('Logged in to %r.', self.name)
                    else:
                        raise notch.agent.errors.ConnectError(
                            'Password not accepted on %r.' % self.name)
 
    def _disconnect(self):
        self._transport.disconnect()

    def _disable_pager(self):
        logging.debug('Disabling pager on %r', self.name)
        self._transport.command('terminal length 0', self._prompt)
        logging.debug('Disabled pager on %r', self.name)

    def _command(self, command, mode=None):
        # mode argument is as yet unused. Quieten pylint.
        _ = mode
        try:
            return self._transport.command(command, self._prompt)
        except (OSError, EOFError, pexpect.EOF), e:
            if command in ('logout', 'exit'):
                pass
            else:
                exc = notch.agent.errors.CommandError(str(e))
                exc.retry = True
                raise exc

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

    LOGIN_PROMPT = 'Username:'
    PASSWORD_PROMPT = re.compile('[Pp]assword:')
    ENABLE_PASSWORD_PROMPT = PASSWORD_PROMPT
    PROMPT = re.compile(r'\S+\s?[>#]')
    ERR_NOT_SETUP = 'Password required, but none set'
    ERR_FULL = 'Sorry, session limit reached'

    ENABLE_CHAR = '#'

    DEFAULT_CONNECT_METHOD = 'sshv2'

    def __init__(self, name=None, addresses=None):
        super(IosDevice, self).__init__(name=name, addresses=addresses)
        self._ssh_client = None
        self.connect_methods = ('telnet', 'sshv2')
        # Not used directly.
        self._port = None

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        port = port or self._port
        connect_method = connect_method or self.connect_method
        if connect_method == 'sshv2' or connect_method is None:
            self._transport = trans_paramiko_expect.ParamikoExpectTransport(
                timeouts=self.timeouts, port=port, address=str(address))
        elif connect_method == 'telnet':
            self._transport = trans_telnet.TelnetDeviceTransport(
                timeouts=self.timeouts, port=port, address=str(address))
        else:
            raise ValueError('Unsupported connect_method: %r' %
                             connect_method)
        # May raise notch.agent.errors.ConnectError
        self._transport.connect(credential)
        self._login(credential.username, credential.password)
        self._get_prompt()
        if credential.enable_password is not None and credential.auto_enable:
            self._enable(credential.enable_password)
        self._disable_pager()

    def _get_prompt(self):
        self._transport.write('\n')
        i = self._transport.expect([self.PROMPT], self.timeouts.resp_short)
        if not i:
            self._prompt = self._transport.match.group(0)
            logging.debug('Expected prompt is now: %r', self._prompt)
            return
        else:
            logging.error('Failed to get prompt on %s', self.name)

    def _enable(self, enable_password):
        logging.debug('Enabling on %r' % self.name)
        self._transport.write('\n')
        try:
            _ = self._transport.expect([self.PROMPT],
                                       self.timeouts.resp_short)
        except (pexpect.EOF, pexpect.TIMEOUT):
            raise notch.agent.errors.EnableError('Could not find prompt prior '
                                                 'to enabling.')

        self._transport.write('enable\n')
        sent_password = False
        while True:
            i = self._transport.expect([self.ENABLE_PASSWORD_PROMPT,
                                        r'timeout expired',
                                        r'% Bad secrets',
                                        self.PROMPT,
                                        pexpect.TIMEOUT,
                                        pexpect.EOF,
                                        ], self.timeouts.resp_short)
            if i == 0 or i == 1:
                if i == 1:
                    logging.debug('Timed out after sending "enable" command.')
                else:
                    self._transport.write(enable_password + '\n')
                    sent_password = True
                continue
            elif i == 2:
                raise notch.agent.errors.AuthenticationError(
                    'Enable authentication failed.')
            elif i == 3:
                # Saw the prompt.
                if (sent_password or
                    self._transport.match.group(0).endswith(self.ENABLE_CHAR)):
                    # Short-circuit the "sent password?" check if
                    # the prompt ends in the enabled prompt word (e.g.,
                    # the device didn't ask us for a password).
                    logging.debug('Enabled on %s', self.name)
                    # The prompt will change when we enable.
                    self._prompt = self._transport.match.group(0)
                    logging.debug('Prompt is now: %r', self._prompt)
                    return
                else:
                    # Consume the buffer and go around, since we already
                    # sent enable.
                    continue
            else:
                raise notch.agent.errors.EnableError(
                    'Failed to enable on %r.' % self.name)

    def _login(self, username, password, connect_method=None):
        # We only need to manually login for the default method, telnet.
        connect_method = connect_method or self.connect_method
        if connect_method == 'telnet':
            self._transport.write('\n')
            i = self._transport.expect(
                [self.LOGIN_PROMPT, self.ERR_NOT_SETUP, self.ERR_FULL,
                 pexpect.TIMEOUT, pexpect.EOF], self.timeouts.resp_short)
            if i > 2:
                # Didn't see anything we expected.
                raise notch.agent.errors.ConnectError(
                    'Did not find login prompt %r.'
                    ' Instead, got %r' % (self.LOGIN_PROMPT,
                                          self._transport.before))
            elif i == 1 or i == 2:
                raise notch.agent.errors.ConnectError(
                    'Device says: %r' % self._transport.match)
            else:
                self._transport.write(username + '\n')
                i = self._transport.expect(
                    [self.PASSWORD_PROMPT, pexpect.TIMEOUT,
                     pexpect.EOF], self.timeouts.resp_short)
                if i:
                    raise notch.agent.errors.ConnectError(
                        'Did not find password prompt %r.'
                        % self.PASSWORD_PROMPT)
                else:
                    self._transport.write(password + '\n')
                    i = self._transport.expect(
                        [self.PROMPT, pexpect.TIMEOUT, pexpect.EOF],
                        self.timeouts.resp_short)
                    if not i:
                        logging.debug('Logged in to %r.', self.name)
                    else:
                        raise notch.agent.errors.ConnectError(
                            'Password not accepted on %r.' % self.name)

    def _disconnect(self):
        try:
            self._transport.write('exit\n')
        except (notch.agent.errors.CommandError,
                OSError, EOFError, pexpect.EOF):
            return
        else:
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

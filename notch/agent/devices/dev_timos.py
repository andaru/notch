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

"""Notch device model for Timetra OS (Timetra/Alcatel) devices."""


import logging
import re
from eventlet.green import socket

import notch.agent.errors

import paramiko
import pexpect

import device
import trans_paramiko_expect


CTRL_C = r'\x03'
CTRL_Z = r'\x16'


class EnableFailedError(Exception):
    pass


class TimosDevice(device.Device):
    """Timetra/Alcatel TimOS device model.

    Connect methods supported:
      sshv2 (via Paramiko in interactive mode with pexpect)
    """

    PROMPT = re.compile(r'\*?[AB]\:([^\$#]+)[\$#]')
    ERR_NOT_SETUP = 'Password required, but none set'

    DEFAULT_CONNECT_METHOD = 'sshv2'
    DEFAULT_PORT = 22

    def __init__(self, name=None, addresses=None):
        super(TimosDevice, self).__init__(name=name, addresses=addresses)
        self.connect_methods = ('sshv2', )
        self._port = self.DEFAULT_PORT
        self._ssh_client = None
        self._transport = None

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        port = port or self._port
        self._transport = trans_paramiko_expect.ParamikoExpectTransport(
            timeouts=self.timeouts, address=str(address), port=port)       
        self._transport.connect(credential)
        self._get_prompt(password=credential.password)
        self._disable_pager()
        # TODO(afort): Handle enabling.
        # if credential.enable_password:
        #     self._enable(credential.enable_password)

    def _get_prompt(self, password=None):
        # Sometimes we get prompted for a password, here.
        while True:
            i = self._transport.expect([self.PROMPT,
                                        '[Pp]assword:',
                                        pexpect.EOF],
                                       self.timeouts.resp_short)
            if i == 0:
                self._prompt = self._transport.match.group(0)
                logging.debug('Expected prompt is now: %r', self._prompt)
                return
            elif i == 1:
                self._transport.write(password + '\n')
                continue               
            elif i == 2:
                e = notch.agent.errors.ConnectError(
                    'Device %s closed connection after login (locked out)'
                    % self.name)
                e.retry = False
                raise e

    def _enable(self, enable_password):
        self._transport.write('enable\n')
        while True:
            i = self._transport.expect([self.PROMPT,
                                        r'[Pp]assword:',
                                        r'timeout expired',
                                        r'% Bad secrets',
                                        ], 10)
            if i == 0:
                logging.debug('Enabled on %s', self.name)
                # The prompt will change when we enable.
                self._prompt = self._transport.match.group(0)
                logging.debug('Prompt is now: %r', self._prompt)
                return
            elif i == 1:
                self._transport.write(enable_password + '\n')
                continue
            elif i == 2:
                continue
            elif i == 3:
                raise notch.agent.errors.AuthenticationError(
                    'Enable authentication failed.')

    def _disconnect(self):
        self._transport.disconnect()

    def _disable_pager(self):
        logging.debug('Disabling pager on %r', self.name)
        self._transport.command('environment no more', self._prompt,
                                command_trailer='\r', expect_trailer='')
        logging.debug('Disabled pager on %r', self.name)

    def _command(self, command, mode=None):
        # mode argument is as yet unused. Quieten pylint.
        _ = mode
        try:
            return self._transport.command(command, self._prompt,
                                           expect_command=False,
                                           command_trailer='\r',
                                           expect_trailer='[^\r]*\r\n')
        except (OSError, EOFError, pexpect.EOF), e:
            if command != 'logout':
                exc = notch.agent.errors.CommandError(str(e))
                exc.retry = True
                raise exc
            else:
                pass
        

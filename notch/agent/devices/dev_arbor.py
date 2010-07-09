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

"""Notch device model for Arbor appliances."""


import logging
import re

import pexpect

import device
import trans_paramiko_expect

import notch.agent.errors


class ArborDevice(device.Device):
    """An Arbor appliance device; OpenSSH server."""

    PROMPT = re.compile(r'.*?@.*?\:/[>%#]\s?')
    ERROR = re.compile(r'^[0-9]{2,4}\: .+')

    DEFAULT_CONNECT_METHOD = 'sshv2'
    DEFAULT_PORT = 22

    # Initial setup (after authentication) can be slow, so allow longer.
    TIMEOUT_RESP_SHORT = 25.0
    
    def __init__(self, name=None, addresses=None):
        super(ArborDevice, self).__init__(name=name, addresses=addresses)
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
        if credential.auto_enable:
            self._enable(credential.enable_password)

    def _get_prompt(self, password=None):
        # Sometimes we get prompted for a password, here.
        while True:
            i = self._transport.expect([self.PROMPT,
                                        '[Pp]assword:',
                                        pexpect.EOF],
                                       self.timeouts.resp_short)
            if i == 0:
                self._prompt = self._transport.match.group(0)
                logging.debug('Expected prompt is: %r', self._prompt)
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

    def _enable(self, unused_enable_password):
        self._transport.write('edit\n')
        while True:
            i = self._transport.expect([self.PROMPT,
                                        self.ERROR],
                                       self.timeouts.resp_short)
            if i == 1:
                logging.error('Could not enable on %s', self.name)
                break
            elif i == 0:
                if self._transport.match.group(0).endswith('# '):
                    logging.debug('Enabled on %s', self.name)
                    self._prompt = self._transport.match.group(0)
                    logging.debug('Expected prompt is: %r', self._prompt)
                else:
                    logging.debug('Did not enable on %s. Matched: %r',
                                  self.name, self._transport.match.group(0))
                break

    def _disconnect(self):
        try:
            # Safely exit both edit mode (if we're in it) and regular mode.
            self._transport.write('exit\n')
            self._transport.write('exit\n')
            self._transport.disconnect()
        except (OSError, EOFError, notch.agent.errors.CommandError):
            return

    def _command(self, command, mode=None):
        # mode argument is as yet unused. Quieten pylint.
        _ = mode
        try:
            return self._transport.command(command, self._prompt,
                                           expect_command=True,
                                           expect_trailer='(\r\n|\n|\r)+')
        except (OSError, EOFError, pexpect.EOF,
                notch.agent.errors.CommandError), e:
            if command != 'exit':
                exc = notch.agent.errors.CommandError(str(e))
                exc.retry = True
                raise exc
            else:
                pass

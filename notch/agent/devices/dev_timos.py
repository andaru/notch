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

from notch.agent import errors

import paramiko

import device
import trans_paramiko_expect


CTRL_Z = r'\x16'


class EnableFailedError(Exception):
    pass


class TimosDevice(device.Device):
    """Timetra/Alcatel TimOS device model."""

    PROMPT = re.compile(r'\S+\s?[>#]')
    ERR_NOT_SETUP = 'Password required, but none set'

    def __init__(self, name=None, addresses=None):
        super(TimosDevice, self).__init__(name=name, addresses=addresses)
        self._port = 22
        self._ssh_client = None
        self._transport = trans_paramiko_expect.ParamikoExpectTransport(
            timeouts=self.timeouts)

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        self._transport.address = str(address)
        self._transport.port = port or self._port
        self._transport.connect(credential)
        self._get_prompt()
        self._disable_pager()
        if credential.enable_password:
            self._enable(credential.enable_password)

    def _get_prompt(self):
        self._transport.write('\n')
        i = self._transport.expect([self.PROMPT], 10)
        if i == 0:
            self._prompt = self._transport.match.group(0)
            logging.debug('Prompt is now: %r', self._prompt)
            return
        else:
            logging.error('Failed to get prompt on %s', self.name)

    def _enable(self, enable_password):
        self._transport.write('enable\n')
        while True:

            i = self._transport.expect([self.PROMPT,
                                        r'Password: ',
                                        r'timeout expired',
                                        r'% Bad secrets',
                                        ], 10)
            if i == -1:
                raise EnableFailedError(self._transport.before)
            elif i == 0:
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
                raise errors.AuthenticationError(
                    'Enable authentication failed.')

    def _disconnect(self):
        self._transport.disconnect()

    def _disable_pager(self):
        logging.debug('Disabling pager')
        self._transport.command('terminal length 0', self._prompt)
        logging.debug('Disabled pager')

    def command(self, command, mode=None):
        # mode argument is as yet unused. Quieten pylint.
        _ = mode
        return self._transport.command(command, self._prompt)

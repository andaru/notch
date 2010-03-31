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

from notch.agent import errors

import device
import trans_telnet


CTRL_Z = r'\x16'


class EnableFailedError(Exception):
    pass


class IosDevice(device.Device):
    """cisco IOS style device model."""   

    LOGIN_PROMPT = 'Username: '
    PASSWORD_PROMPT = 'Password: '
    PROMPT = re.compile(r'\S+\s?[>#]')
    ERR_NOT_SETUP = 'Password required, but none set'
    
    def __init__(self, name=None, addresses=None):
        super(IosDevice, self).__init__(name=name, addresses=addresses)
        self._ssh_client = None
        self._port = 23
        self._transport = trans_telnet.TelnetDeviceTransport()
       
    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        self._transport.address = str(address)
        self._transport.port = port
        self._transport.connect()
        self._login(credential.username, credential.password)
        # TODO(afort): Add .autoenable to the credential record.
        self._enable(credential.enable_password)
        self._disable_pager()
        
    def _enable(self, enable_password):
        self._transport.write('enable\n')
        while True:
            i, matchobj, pretext = self._transport.expect([self.PROMPT,
                                                           r'Password: ',
                                                           r'timeout expired',
                                                           r'% Bad secrets',
                                                           ], 10)
            if i == -1:
                raise EnableFailedError(pretext)
            elif i == 0:
                logging.debug('Enabled on %s', self.name)
                # The prompt will change when we enable.
                self._prompt = matchobj.group(0)
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

    def _login(self, username, password):
        self._transport.write('\n')
        i, matchobj, pretext = self._transport.expect([self.LOGIN_PROMPT,
                                                       self.ERR_NOT_SETUP], 10)
        if i == -1:
            # Didn't see anything we expected.
            raise errors.ConnectError('Did not find login prompt %r.' %
                                     self.LOGIN_PROMPT)
        elif i == 1:
            pretext = pretext.lstrip()
            raise errors.ConnectError('Device says: %r' % pretext)
        else:
            self._transport.write(username + '\n')
            i, matchobj, pretext = self._transport.expect(
                [self.PASSWORD_PROMPT], 10)
            if i == - 1:
                raise errors.ConnectError('Did not find password prompt %r.' %
                                          self.PASSWORD_PROMPT)
            else:
                self._transport.write(password + '\n')
                i, matchobj, pretext = self._transport.expect(
                    [self.PROMPT], 10)
                if i == -1:
                    raise errors.ConnectError(
                        'Did not find the command prompt after login.')
                else:
                    self._prompt = matchobj.group(0)
                    logging.debug('Prompt is now: %r', self._prompt)

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

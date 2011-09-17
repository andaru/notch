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

"""Notch device model for Nortel (ex-Bay) switches.

Attempts to deal with the BPS (Bay/Business Policy Switch) and the
Baystack series of switches.  This should also include Nortel 3510 and 5510
switch products, which are members of the same line of products.

This module presently uses the IOS device support as a basis.
SSH support is as yet untested.
"""


import logging
import re

import pexpect

import notch.agent.errors

import dev_ios


class BayDevice(dev_ios.IosDevice):
    """A Nortel/Bay Ethernet Switch device model."""

    PRE_LOGIN_PROMPT = 'Enter Ctrl-Y to begin'
    CLI_MENU_OPTION = 'ommand Line Interface'
    PASSWORD_PROMPT = 'Enter Password:'
    ERR_INVALID_INPUT = 'Invalid input detected'
    ERR_INVALID_PASSWORD = re.compile('nvalid [pP]assword')
    PROMPT = re.compile(r'[^\n\r]+\s?[>#]')
    PAGER = re.compile(r'(\-{4}.*More.*\-{4}|\-\-More\-\-)')
    POST_PAGER = re.compile(r'(\x08\x08 )*')

    def __init__(self, name=None, addresses=None):
        super(BayDevice, self).__init__(name=name, addresses=addresses)

    def _disconnect(self):
        try:
            self._transport.write('logout\n')
            i = self._transport.expect(
                ['ogout\.\.', pexpect.TIMEOUT, pexpect.EOF],
                self.timeouts.resp_short)
            if i > 0:
                return
            else:
                self._transport.write('L')
        except (notch.agent.errors.CommandError,
                OSError, EOFError, pexpect.EOF):
            return
        else:
            self._transport.disconnect()

    def _command(self, command, mode=None):
        # mode argument is as yet unused. Quieten pylint.
        _ = mode
        try:
            return self._transport.command(command, self._prompt,
                                           expect_trailer='\r',
                                           pager=self.PAGER,
                                           strip_chars=['\b ','\b'])
        except (OSError, EOFError, pexpect.EOF, pexpect.TIMEOUT), e:
            if command in ('logout', 'exit'):
                pass
            else:
                exc = notch.agent.errors.CommandError(str(e))
                exc.retry = True
                raise exc

    def _disable_pager(self):
        logging.debug('Disabling pager on %r', self.name)
        self._command('terminal length 0')
        self._command('terminal width 132')
        logging.debug('Disabled pager on %r', self.name)

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        super(BayDevice, self)._connect(address=address,
                                        port=port,
                                        connect_method=connect_method,
                                        credential=credential)
        self._transport.strip_ansi = True
        self._transport.dos2unix = True

    def _login(self, username, password, connect_method=None):
        # We only need to manually login for the default method, telnet.
        # XXX that this may not be the case for SSH, which is untested.
        connect_method = connect_method or self.connect_method
        if connect_method == 'telnet':
            i = self._transport.expect(
                [self.PRE_LOGIN_PROMPT, pexpect.TIMEOUT, pexpect.EOF],
                self.timeouts.resp_short)
            if i > 0:
                raise notch.agent.errors.ConnectError(
                    'Device says: %r' % self._transport.before)
            else:
                # Send a Control Y to get the password prompt.
                self._transport.write(chr(25))

                i = self._transport.expect(
                    [self.PASSWORD_PROMPT, self.CLI_MENU_OPTION,
                     pexpect.TIMEOUT, pexpect.EOF], self.timeouts.resp_short)
                if i > 1:
                    raise notch.agent.errors.ConnectError(
                        'Did not find password prompt %r.'
                        % self.PASSWORD_PROMPT)
                # Either we're in, or we saw the password prompt.
                # If we got asked for the password, send it.
                if not i:
                    self._transport.write(password + '\n')
                    # Next, expect the CUA menu option to appear.
                    i = self._transport.expect(
                        [self.CLI_MENU_OPTION, self.ERR_INVALID_PASSWORD,
                         pexpect.TIMEOUT, pexpect.EOF],
                        self.timeouts.resp_short)
                    if not i:
                        # Logged into CLI mode.
                        logging.debug('Logged in to %r.', self.name)
                    elif i > 0:
                        raise notch.agent.errors.ConnectError(
                            'Password not accepted on %r.' % self.name)

                self._transport.write('C')
                i = self._transport.expect(
                    [self.PROMPT, pexpect.TIMEOUT,
                     pexpect.EOF], self.timeouts.resp_short)
                if i > 0:
                    raise notch.agent.errors.ConnectError(
                        'Did not find CLI mode prompt %r.'
                        % self.PASSWORD_PROMPT)
                logging.debug('Switched to CLI mode on %r.', self.name)

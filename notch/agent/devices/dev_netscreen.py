#!/usr/bin/env python
#
# Copyright 2010 Andrew Fort. All Rights Reserved.
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

"""Notch device model for Netscreen ScreenOS operating system."""


import logging
import re

import pexpect

import notch.agent.errors

import dev_ios


class ScreenosDevice(dev_ios.IosDevice):
    """Netscreen ScreenOS device.

    Connect methods supported:
      sshv2 (via Paramiko in interactive mode with pexpect)
    """

    PROMPT = re.compile(r'\S+\s?->')
    UNSAVED_CONFIG = re.compile(r'Configuration modified, save\?')

    def __init__(self, name=None, addresses=None):
        super(ScreenosDevice, self).__init__(name=name, addresses=addresses)
        self.connect_methods = ('sshv2', )

    def _disable_pager(self):
        logging.debug('Disabling pager on %r', self.name)
        self._transport.command('set console page 0', self._prompt)
        logging.debug('Disabled pager on %r', self.name)

    def _enable(self, enable_password):
        pass

    def _disconnect(self):
        try:
            self._transport.write('exit\n')
            i = self._transport.expect([self.UNSAVED_CONFIG,
                                        pexpect.EOF,
                                        pexpect.TIMEOUT],
                                       self.timeouts.resp_short)
            if i == 0:
                # No trailing newline necessary on test units.
                self._transport.write('n')
            return
        except (notch.agent.errors.CommandError,
                OSError, EOFError, pexpect.EOF):
            return
        else:
            self._transport.disconnect()

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

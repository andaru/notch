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

"""Notch device model for Nortel ESR devices.

Attempts to deal with the ESR8xxx and ESR18xx series devices.

This module presently uses the IOS device support as a basis,
though SSH support is untested and so, as yet, disabled.
"""


import logging
import re

import pexpect

import notch.agent.errors

import dev_ios


class EsrDevice(dev_ios.IosDevice):
    """A Nortel Ethernet Routing Switch (or ESR) class device model."""

    LOGIN_PROMPT = 'Login:'
    PROMPT = re.compile(r'.+\s?[>\#]')

    def _disconnect(self):
        try:
            self._transport.write('logout\n')
        except (notch.agent.errors.CommandError,
                OSError, EOFError, pexpect.EOF):
            return
        else:
            self._transport.disconnect()

    def _disable_pager(self):
        logging.debug('Disabling pager on %r', self.name)
        self._transport.command('config cli more false', self._prompt)
        logging.debug('Disabled pager on %r', self.name)

    def __init__(self, name=None, addresses=None):
        super(EsrDevice, self).__init__(name=name, addresses=addresses)

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

"""Notch device model for Alcatel-Lucent Omniswitch devices."""

import re

import device
import dev_ios


class OmniswitchDevice(dev_ios.IosDevice):
    """Alcatel-Lucent Omniswitch device model.

    Connect methods supported:
      sshv2 (via Paramiko in interactive mode with pexpect)
      telnet (via telnetlib)
    """

    LOGIN_PROMPT = 'login :'
    PASSWORD_PROMPT = 'password :'
    PROMPT = re.compile('\-\> ')

    # Sometimes Omniswitches have a long login delay; be understanding.
    TIMEOUT_RESP_SHORT = 17.0

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        super(OmniswitchDevice, self)._connect(address=address,
                                               port=port,
                                               connect_method=connect_method,
                                               credential=credential)
        # Omniswitches return DOS CRLF responses - fix this.
        self._transport.dos2unix = True

    def _enable(self, enable_password):
        """The Alcatel-Lucent Omniswitch has no enable mode."""
        pass

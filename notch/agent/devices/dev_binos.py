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

"""Notch device model for devices running NOS.

NOS is a CLI/Operating System operating on OLT/ONU equipment.
"""

import pexpect

import dev_ios


class BinosDevice(dev_ios.IosDevice):
    """A BiNOS device.

    Similar to an IOS device.
    """

    def _command(self, command, mode=None):
        # mode argument is as yet unused. Quieten pylint.
        _ = mode
        try:
            return self._transport.command(command, self._prompt,
                                           expect_trailer='\n',
                                           expect_command=False)
        except (OSError, EOFError, pexpect.EOF, pexpect.TIMEOUT), e:
            if command in ('logout', 'exit'):
                pass
            else:
                exc = notch.agent.errors.CommandError(str(e))
                exc.retry = True
                raise exc

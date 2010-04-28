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

"""Device object factory function.

Update this module when adding a new vendor device model. The 'vendor'
string relates to a vendor operating system (e.g., 'juniper' for Juniper
JunOS), and must match the vendor string for devices in the configuration
(e.g., DNS TXT records or router.db files).
"""

from notch.agent.devices import dev_binos
from notch.agent.devices import dev_ios
from notch.agent.devices import dev_junos
from notch.agent.devices import dev_nos
from notch.agent.devices import dev_timos


VENDOR_MAP = {'cisco': dev_ios.IosDevice,
              'juniper': dev_junos.JunosDevice,
              'nos': dev_nos.NosDevice,
              'timetra': dev_timos.TimosDevice,
              'telco': dev_binos.BinosDevice,
              }


def new_device(name, vendor, addresses=None):
    """Factory function to generate a new device.Device subclass.

    Args:
      name: A string, the device hostname.
      device_type: A string, the device type (aka vendor) name.
        This field determines which subclass will be chosen.
      addresses: A list of strings, IP addresses to reach the device's
        primary management interface.

    Returns:
      A concrete subclass of device.Device, a device object for the device type.

    Raises:
      KeyError: The vendor name was unknown.
    """
    if vendor not in VENDOR_MAP:
        raise KeyError('Device type/vendor %r is not valid.' % vendor)
    return VENDOR_MAP[vendor](name=name, addresses=addresses)

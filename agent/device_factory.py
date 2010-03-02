#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Device object factory function.

Update this module when adding a new vendor device model. The 'vendor'
string relates to a vendor operating system (e.g., 'juniper' for Juniper
JunOS), and must match the vendor string for devices in the configuration
(e.g., DNS TXT records or router.db files).
"""


import dev_junos


VENDOR_MAP = {'junos': dev_junos.JunosDevice,
              'juniper': dev_junos.JunosDevice}


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

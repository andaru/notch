#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Exceptions, error handlers and counters."""

import threading

# Mutex used to protect counters.
mu = threading.Lock()


# Error classes.

class Error(Exception):
    pass


class ApiError(Error):
    """Errors emitted in response to an API call."""
    dampen_reconnect = False

    def __init__(self, *args, **kwargs):
        super(ApiError, self).__init__(*args, **kwargs)
        self.name = self.__class__.__name__
        self.msg = self.__class__.__doc__


class ConnectError(ApiError):
    """There was an error connecting to a device."""
    dampen_reconnect = True


class CommandError(ApiError):
    """There was an error whilst executing a command on a device."""


class DeviceWithoutAddressError(ApiError):
    """The device does not have an IP address."""


class DisconnectError(ApiError):
    """There was an error disconnecting from a device."""


class InvalidDeviceError(ApiError):
    """The device is not yet initialised."""


class InvalidModeError(ApiError):
    """The mode chosen for the API call was unsupported by the device."""


class InvalidRequestError(ApiError):
    """The method name being requested was not defined by the device API."""


class NoAddressesError(ApiError):
    """The device name has no addresses associated with it."""


class NoSuchVendorError(ApiError):
    """The vendor requested does not exist as a device model."""


class NoSessionCreatedError(ApiError):
    """No session could be created for the requested arguments."""


def tornadorpc_handle(exc):
    """Handles the exception for the tornadorpc framework and counts it."""
    
    
    

# Errors used in tornadorpc library for responses. Adds to existing JSON/XML
# RPC error codes. Key integers correspond to the 'code' attribute on ApiError
# sub-classes.

error_dictionary = {
    1: ConnectError,
    2: DisconnectError,
    3: InvalidDeviceError,
    4: InvalidModeError,
    5: InvalidRequestError,
    6: NoAddressesError,
    7: NoSuchVendorError,
    8: NoSessionCreatedError,
}

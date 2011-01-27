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

"""Exceptions, error handlers and counters."""


# Error classes.

class Error(Exception):
    pass


class ConfigError(Error):
    """Configuration errors."""


class ConfigMissingRequiredSectionError(ConfigError):
    """The config was missing a required section."""


class CredentialError(Error):
    """Credential errors."""


class MissingFieldError(CredentialError):
    """The credential was missing a required field."""


class UnknownConfigurationFileFormatError(ConfigError):
    """The config file extension (and thus, format) was unrecognised."""


class UnknownCredentialsFileFormatError(CredentialError):
    """The file extension (and thus, format) was unrecognised."""


# Notch API error classes.

class ApiError(Error):
    """Errors emitted in response to an API call."""
    dampen_reconnect = False
    disconnect_on_error = False
    retry = False

    def __init__(self, *args, **kwargs):
        super(ApiError, self).__init__(*args, **kwargs)
        self.name = self.__class__.__name__
        self.msg = self.__class__.__doc__


class AuthenticationError(ApiError):
    """Device authentication (either login or enable) failed."""

    
class ConnectError(ApiError):
    """There was an error connecting to a device."""
    dampen_reconnect = True


class CommandError(ApiError):
    """There was an error whilst executing a command on a device."""
    disconnect_on_error = True

    
class DownloadError(ApiError):
    """There was an error whilst downloading a file from the device."""

    
class DeviceWithoutAddressError(ApiError):
    """The device does not have an IP address."""


class DisconnectError(ApiError):
    """There was an error disconnecting from a device."""


class EnableError(ApiError):
    """There was an error attempting to receive enable authorization."""


class EOFError(ApiError):
    """End of file received from device."""
    retry = True


class InvalidDeviceError(ApiError):
    """The device is not yet initialised."""


class InvalidModeError(ApiError):
    """The mode chosen for the API call was unsupported by the device."""


class InvalidRequestError(ApiError):
    """The method name being requested was not defined by the device API."""


class NoAddressesError(ApiError):
    """The device name has no addresses associated with it."""


class NoMatchingCredentialError(ApiError, CredentialError):
    """There was no matching credential for your request."""

    
class NoSuchDeviceError(ApiError):
    """The device name requested is not known to the system."""

    
class NoSuchVendorError(ApiError):
    """The vendor requested does not exist as a device model."""


class NoSessionCreatedError(ApiError):
    """No session could be created for the requested arguments."""


class UploadError(ApiError):
    """There was an error whilst uploading a file from the device."""


def rpc_error_handler(exc, rpc):
    """Handles an RPC error.

    Args:
      exc: An Exception instance, the error.
      rpc: A tornadorpc RPCParser instance (JSONRPCParser or XMLRPCParser).
    """
    if hasattr(rpc, 'faults'):
        err = getattr(rpc.faults, exc.__class__.__name__, None)
        if err is not None:
            return err(str(exc))
        else:
            return rpc.faults.internal_error(str(exc))
    else:
        return rpc.faults.internal_error(str(exc))


# Errors used in tornadorpc library for responses. Added to existing JSON/XML
# RPC error codes. Key integers correspond to the 'code' attribute on ApiError
# sub-classes.

error_dictionary = {
    'ConnectError': 1,
    'DisconnectError': 2,
    'InvalidDeviceError': 3,
    'InvalidModeError': 4,
    'InvalidRequestError': 5,
    'NoAddressesError': 6,
    'NoSuchVendorError': 7,
    'NoSessionCreatedError': 8,
    'AuthenticationError': 9,
    'CommandError': 10,
    'EOFError': 11,
    'NoMatchingCredentialError': 12,
    'DownloadError': 13,
    'UploadError': 14,
    'NoSuchDeviceError': 15,
    'EnableError': 16,
}

reverse_error_dictionary = dict((v, k) for (k, v) in error_dictionary.items())

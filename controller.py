#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Notch Agent controller.

The controller manages device sessions and control flow handling for
the RPC server. Routine maintenance activities are also located here.
"""


import collections
import logging

import credential
import device_factory
import device_manager
import errors
import lru
import notch_config
import session



# Maximum number of active sessions (held in LRU at any one time)
MAX_ACTIVE_SESSIONS = 128


class Error(Exception):
    """Module-level exception."""


class AddressLookupError(Error):
    """There was an error during address lookup."""


class Controller(object):
    """The Notch Agent Controller.

    Attributes:
      sessions: A lru.LruDict of session.Session objects, keyed by
        session.SessionKey namedtuples.
      config: A dict, holding the configuration.
      device_manager: A device_manager.DeviceManager instance.
    """

    def __init__(self, config=None):
        self.sessions = lru.LruDict(populate_callback=self.create_session,
                                    expire_callback=self.expire_session,
                                    maximum_size=MAX_ACTIVE_SESSIONS)
        self.config = config or {}
        self.device_manager = device_manager.DeviceManager(self.config)
        self.load_credentials()

    def load_credentials(self):
        self.credentials = None
        options_section = self.config.get('options')
        if not options_section:
            logging.error('No options section found in configuration')
            return
        creds_filename = options_section.get('credentials')
        if creds_filename is None:
            logging.error('No credentials filename found in options section')
        else:
            logging.debug('Loading credentials from file %r', creds_filename)
            self.credentials = credential.load_credentials_file(creds_filename)

        
    def create_session(self, key):
        """Creates a session.Session object for the session key.

        No exceptions are raised here (due to this being a callback
        executed by the LRU cache).

        Args:
          key: A session.SessionKey object, the session key.

        Returns:
          A session.Session object, or None if a session couldn't be made.
        """
        device_info = self.device_manager.device_info(key.device_name)

        if device_info:
            device = device_factory.new_device(
                device_info.device_name, device_info.device_type,
                addresses=device_info.addresses)
            return session.Session(device=device)
        else:
            logging.error('Device %r unknown', key.device_name)
            return None

    def expire_session(self, unused_session_key, session_value):
        """LRU cache expiry callback for the sessions cache."""
        session_value.disconnect()

    def get_session(self, **kwargs):
        """Returns a session matching the keyword arguments.

        Args:
          kwargs: Dict of keyword arguments for the session key, inc. keys
          'device_name', 'connect_method', 'user', 'privilege_level')

        Returns:
          A session.Session object, or None if no session could be created.
        """
        # Generate the session key from arguments.
        device = kwargs.get('device_name')
        if device is None:
            raise ValueError('Request arguments %r did not contain a '
                             'device_name.' % kwargs)

        # TODO(afort): Load default values here from configuration.
        connect_method = kwargs.get('connect_method')
        user = kwargs.get('user')
        privilege_level = kwargs.get('privilege_level')

        key = session.SessionKey(device_name=device,
                                 connect_method=connect_method,
                                 user=user, privilege_level=privilege_level)
        try:
            return self.sessions[key]
        except KeyError:
            return None

    def request(self, method, **kwargs):
        """Executes a request.

        Args:
          method: A string, the device API method name.
          kwargs: A dict, the keyword arguments for the request.

        Returns:
          Either an errors.Error subclass instance (when the request ends
          in error), or a string being the method response.
        """
        session = self.get_session(**kwargs)

        if session is None:
            raise errors.NoSessionCreatedError(
                'No session available for request arguments %r' % kwargs)

        if self.credentials and 'device_name' in kwargs:
            session.credential = self.credentials.get_credential(
                kwargs['device_name'])
        try:
            return session.request(method, **kwargs)
        except errors.ApiError, e:
            # TODO(afort): API errors cause an error response over the wire.
            logging.error(str(e))
        except errors.Error, e:
            # TODO(afort): Should these be being raised?
            logging.error(str(e))

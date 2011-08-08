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

"""Notch Agent controller.

The controller manages device sessions and control flow handling for
the RPC server. Routine maintenance activities are also located here.
"""

import eventlet

import logging
from eventlet.green import time

import notch.agent.errors

import credential
import device_factory
import device_manager
import lru
import session


# Maximum number of active sessions held in LRU at any one time.
# TODO(afort): Make configurable.
MAX_ACTIVE_SESSIONS = 512
# Default session check window period in seconds.
DEFAULT_SESSION_CHECK_PERIOD_S = 10.0


class Controller(object):
    """The Notch Agent Controller.

    Attributes:
      sessions: A lru.LruDict of session.Session objects, keyed by
        session.SessionKey namedtuples.
      config: A dict, holding the configuration.
      device_manager: A device_manager.DeviceManager instance.
    """

    def __init__(self, config=None):
        """Initializer.

        Args:
          config: A dict, holding the configuration.
        """
        self.config = config or {}
        self._get_timers_from_config(config)
        self.sessions = lru.LruDict(populate_callback=self.create_session,
                                    expire_callback=self.expire_session,
                                    maximum_size=MAX_ACTIVE_SESSIONS)
        self.device_manager = device_manager.DeviceManager(self.config)
        self.load_credentials()
        self._stopped = eventlet.event.Event()
        self.__current_maint_thread = None

    def stop(self):
        self._stopped.send()
        logging.debug('Disconnecting all sessions.')
        for session in self.sessions.values():
            session.disconnect()

    def run_maintenance(self):
        """Runs maintenance greenthreads."""
        self._session_idle_check()
        self._stopped.wait()

    def _get_timers_from_config(self, config):
        self._session_maint_period = DEFAULT_SESSION_CHECK_PERIOD_S
        timers = self.config.get('timers')
        if timers:
            try:
                self._session_maint_period = float(
                    timers.get('session_maint_period',
                               DEFAULT_SESSION_CHECK_PERIOD_S))
            except ValueError:
                pass

    def _session_idle_check(self):
        """Checks the idle timeouts for all sessions."""
        start = time.time()
        for session in self.sessions.values():
            if session is None:
                continue
            elif not session.idle or not session.connected:
                continue
            elif (time.time() > (session.time_last_request or 0) +
                  session.device.MAX_IDLE_TIME):
                logging.debug('Session disconnect (idle for %d sec): %s',
                              session.device.MAX_IDLE_TIME,
                              session.device.name)
                session.disconnect()
        # Re-schedule ourself for execution.
        elapsed = max(0, time.time() - start)
        wait_time = max(0, self._session_maint_period - elapsed)
        eventlet.spawn_after(
            wait_time, self._session_idle_check)

    def load_credentials(self):
        """Loads the credentials store (login passwords/keys)."""
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
          A session.Session object.

        Raises:
          NoSuchDeviceError: The device did not exist.
        """
        device_info = self.device_manager.device_info(key.device_name)

        if device_info:
            device = device_factory.new_device(
                device_info.device_name, device_info.device_type,
                addresses=device_info.addresses)
            return session.Session(device=device)
        else:
            raise notch.agent.errors.NoSuchDeviceError('Unknown device %r'
                                                       % key.device_name)

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

        Raises:
          The callback on self.sessions may raise an Exception, see its
          population method for more info.

          NoSessionCreatedError: The request arguments were invalid.
        """
        # Generate the session key from arguments.
        device = kwargs.get('device_name')
        if device is None:
            raise notch.agent.errors.NoSessionCreatedError(
                'Request arguments %r did not contain a device_name.' % kwargs)

        # TODO(afort): Load default values here from configuration.
        connect_method = kwargs.get('connect_method')
        user = kwargs.get('user')
        privilege_level = kwargs.get('privilege_level')

        key = session.SessionKey(device_name=device,
                                 connect_method=connect_method,
                                 user=user, privilege_level=privilege_level)

        try:
            # Note: Other exceptions than KeyError may occur.
            return self.sessions[key]
        except KeyError:
            return None

    def request(self, method, **kwargs):
        """Executes a Notch device API request.

        Args:
          method: A string, the device API method name.
          kwargs: A dict, the keyword arguments for the request.

        Returns:
          Either an errors.Error subclass instance (when the request ends
          in error), or a string being the method response.

        Raises:
          notch.agent.errors.NoSuchDeviceError if there was no device supplied
        """
        session = self.get_session(**kwargs)
        if session is None:
            raise notch.agent.errors.NoSessionCreatedError(
                'No session available for request arguments %r' % kwargs)
        if 'device_name' not in kwargs:
                raise notch.agent.errors.NoSuchDeviceError(
                    'No device_name argument in request')
        try:
            # TODO(afort): What if there's no credentials.
            if self.credentials and 'device_name' in kwargs:
                session.credential = self.credentials.get_credential(
                    kwargs['device_name'])
                return session.request(method, **kwargs)
            else:
                raise notch.agent.errors.NoMatchingCredentialError(
                    'No credentials for host %r' % kwargs['device_name'])
        except notch.agent.errors.Error, e:
            raise
        except Exception, e:
            # 'Exceptional' exceptions occuring here are masked poorly
            # by the returned error (usually 'Invalid Params'), so
            # give the developer something to go by.
            logging.error('%s: %s', str(e.__class__), str(e), exc_info=True)
            raise

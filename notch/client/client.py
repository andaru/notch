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

"""The Notch Python client library."""

import eventlet
# Need to monkey patch due to lazy socket references in httplib, used
# by jsonrpclib.
eventlet.monkey_patch(all=True)

import logging
import os
import traceback
from eventlet.green import socket

import jsonrpclib

import lb_transport


# Use at most this number of green threads. Default also influenced by
# setting NOTCH_CONCURRENCY environment variable.
DEFAULT_NOTCH_CONCURRENCY = 50


# Error classes.

class Error(Exception):
    pass


class TimeoutError(Error):
    """The client request timed out."""


class NoAgentsError(Error):
    """No agent addresses were passed to the client."""


class NoCallbackError(Error):
    """The client got an response for a request but has no callback to run."""


class NoSuchLoadBalancingPolicyError(Error):
    """The requested load balancing policy does not exist."""


class UnknownCommandError(Error):
    """The request contained an unknown command."""


class Request(object):
    """An Notch Request object.

    Attributes:
      notch_method: A string, the Notch device API method to call.
      arguments: A dict, the keyword arguments for the request.
      callback: A callable, if not None, call this callback with this
        object when the request has been processed in asynchronous mode.
      callback_args: Positional arguments for the request callback.
      callback_kwargs: Keyword arguments for the request callback.
      result: A string, the method result (or None if the request has not
        yet completed).
      error: An exception if one occured during the request, or None if
        there was no error (or the request has not yet completed).
      valid: A boolean, True if the request part of the object is valid.
      completed: A boolean, True if the request has completed.
      timeout_s: A float, the request timeout, in seconds. If None, do
        not use a timeout on the client side.
    """

    def __init__(self, notch_method, arguments=None,
                 callback=None, callback_args=None, callback_kwargs=None,
                 timeout_s=None):
        # Request arguments.
        self.notch_method = notch_method
        self.arguments = arguments
        self.callback = callback
        self.callback_args = callback_args or tuple()
        self.callback_kwargs = callback_kwargs or {}
        self.timeout_s = timeout_s
        # Response attributes.
        self.result = None
        self.error = None
        # An eventlet timeout instance.
        self._timeout = None
        # Timers available for debugging.
        self.time_sent = None
        self.time_completed = None
        self.time_elapsed_s = None

    valid = property(lambda x: (x.notch_method and x.arguments))
    completed = property(lambda x: x._completed())

    def _completed(self):
        if self._timeout is not None:
            return ((self.result is not None
                     or self.error is not None)
                    and not self._timeout.pending)
        else:
            return (self.result is not None or self.error is not None)

    def start(self):
        if self.timeout_s is not None:
            self._timeout = eventlet.timeout.Timeout(self.timeout_s,
                                                     TimeoutError)

    def finish(self):
        if self._timeout is not None and not self.completed:
            self._timeout.cancel()


class Connection(object):
    """A connection to one or more Notch agents.

    After creating a Client instance, you call Notch API methods and
    provide callbacks to receive the results after the I/O operations
    complete.

    Example:
      import notch.client
      c = notch.client.Connection('localhost:8800')
      req = notch.client.Request('command', {'device_name': 'ar1.foo',
                                             'command': 'show version'})
      ar1_show_ver_output = c.exec_request(req).result

    Asynchronous operation is possible, see the callback* attributes
    on the Request object (and the keyword arguments for the
    exec_request method here).

    Attributes:
      agents: An iterable of strings, host:port pairs for Notch Agents.
        Also accepts a string for a single agent host:port pair.
      max_concurrency: An int, maximum number of concurrent requests to make.
      path: The URL to access the Notch RPC endpoint on all agents.
      load_balancing_policy: The name of the load-balancing transport class.
    """

    # Prefix of all Notch API method names.
    API_METHOD_PREFIX = '_notch_api_'

    def __init__(self, agents=None, max_concurrency=None,
                 path='/JSONRPC2',
                 use_ssl=False, load_balancing_policy=None):
        """Initializer.

        Args:
          use_ssl: A boolean, if True, use HTTPS instead of HTTP for transport.

        Raises:
          NoAgentsError: If no agents were supplied.
        """
        if isinstance(agents, str):
            self.agents = [agents]
        else:
            self.agents = agents or os.getenv('NOTCH_AGENTS')
        try:
            self.max_concurrency = int(max_concurrency or
                                       os.getenv('NOTCH_CONCURRENCY') or
                                       DEFAULT_NOTCH_CONCURRENCY)
        except ValueError:
            self.max_concurrency = DEFAULT_NOTCH_CONCURRENCY

        self.path = path
        if use_ssl:
            self._protocol = 'https://'
        else:
            self._protocol = 'http://'

        self._lb_policy = None
        if load_balancing_policy:
            if hasattr(lb_transport, load_balancing_policy):
                self._lb_policy = getattr(lb_transport, load_balancing_policy)
            else:
                raise NoSuchLoadBalancingPolicyError(
                    'There is no load balancing policy named %r'
                    % load_balancing_policy)

        self._pool = eventlet.greenpool.GreenPool(self.max_concurrency)
        self._notch = None
        self._transport = None
        self._setup_agents()

    def _request_callback(self, gt, *args, **kwargs):
        """Asynchronously receives responses and runs the user callback.

        Args:
          gt: A GreenThread, the thread that completed.
          args: Tuple of arguments for the user callback.
          kwargs: Dict of keyword arguments for the user callback.

        Raises:
          NoCallbackError: The request had no callback.
        """
        # wait() returns immediately as we have been called.
        request = gt.wait()
        if request is not None:
            request.finish()
            if request.callback is not None:
                request.callback(request, *args, **kwargs)
            else:
                raise NoCallbackError(
                    'Asynchronous mode used without defined callback.')

    def _send_notch_api_request(self, method, request, kwarg_list):
        try:
            func = getattr(self._notch, method)
            args = dict((kwarg, request.arguments.get(kwarg, None)) for
                        kwarg in kwarg_list)
            request.result = func(**args)
        except socket.error, e:
            # Use a "too many open files" error to set the concurrency
            # limit to the current usage level.
            if e.args[0] == 24:
                self.max_concurrency = self.num_requests_running - 1
                self._pool.resize(self.max_concurrency)
                logging.debug('Reconfigured GreenThread pool size to %d',
                              self.max_concurrency)
            request.error = e
        except Exception, e:
            request.error = e
        return request

    def _notch_api_command(self, request):
        """Requests the 'command' method via Notch RPC."""
        return self._send_notch_api_request(
            'command', request, ('device_name', 'command', 'mode'))

    def _notch_api_devices_matching(self, request):
        return self._send_notch_api_request(
            'devices_matching', request, ('regexp', ))

    def _setup_agents(self):
        """Sets up the Notch JSON RPC agent connection.

        Raises:
          NoAgentsError: If no agents were supplied.
        """
        if not self.agents:
            raise NoAgentsError('No Notch agents supplied to Client.')
        else:
            self._transport = lb_transport.LoadBalancingTransport(
                hosts=self.agents, transport=jsonrpclib.Transport,
                policy=self._lb_policy)
            self._notch = jsonrpclib.ServerProxy(
                self._protocol + str(self.path), transport=self._transport)

    def _exec_requests(self, requests):
        """Executes a iterable of requests.

        Args:
          requests: An iterable of Request objects.

        Returns:
          A list of Request objects, being any synchronous responses.
          None if there were only asynchronous requests, or no responses.
        """
        # For synchronous mode responses.
        results = []
        for r in requests:
            method = getattr(
                self, self.API_METHOD_PREFIX + r.notch_method, None)
            if method is not None:
                # Get a threenthread to run the method in and start
                # the request timer.
                gt = self._pool.spawn(method, r)
                r.start()
            else:
                raise UnknownCommandError('%r is not a Notch API method.'
                                          % r.notch_method)
            if r.callback is None:
                # Wait for synchronous responses.
                r = gt.wait()
                r.finish()
                results.append(r)
            else:
                # Setup callback method for asynchronous responses.
                gt.link(self._request_callback,
                        *r.callback_args, **r.callback_kwargs)
        if results:
            # Return any synchronous results.
            return results
        else:
            return None

    def exec_request(self, request, callback=None, args=None, kwargs=None):
        """Executes a NotchRequest in this client.

        To execute multiple NotchRequests at once, see the exec_requests
        method.

        Args:
          request: A NotchRequest to execute.
          callback: None or a callable. If not None, uses asynchronous mode,
            calling the callback with request, *args and **kwargs as arguments.
          args: Tuple of arguments for the user callback.
          kwargs: Dict of keyword arguments for the user callback.

        Returns:
          The updated request object in synchronous mode, or None in async mode.
          Inspect the result or error attributes of the request object.
        """
        if callback: request.callback = callback
        if args: request.callback_args = args
        if kwargs: request.callback_kwargs = kwargs
        result = self._exec_requests([request])
        if result is None:
            return result
        else:
            return result[0]

    def exec_requests(self, requests, callback=None, args=None, kwargs=None):
        """Plural form of exec_request. Executes many requests.

        Callback, args and kwargs aruments passed will override those
        on every request in the requests iterable.

        Args:
          requests: NotchRequests to execute.
          callback: None or a callable. If not None, uses asynchronous mode,
            calling the callback with request, *args and **kwargs as arguments.
          args: Tuple of arguments for the user callback.
          kwargs: Dict of keyword arguments for the user callback.
        """
        for request in requests:
            if callback: request.callback = callback
            if args: request.callback_args = args
            if kwargs: request.callback_kwargs = kwargs
        return self._exec_requests(
            requests, callback=callback, args=args, kwargs=kwargs)

    def wait_all(self):
        """Waits for all outstanding requests to complete.

        Useful when running a client without a user interface.
        """
        self._pool.waitall()

    num_requests_running = property(lambda x: x._pool.running())
    num_requests_waiting = property(lambda x: x._pool.waiting())

    # xmlrpclib style Proxy methods. If one initialises
    # notch.client.Client instead of an xmlrpclib server proxy, these
    # methods are API compatible, with added asynchornous callback
    # functionality.

    def command(self, device_name, command=None, mode=None,
                callback=None, callback_args=None, callback_kwargs=None):
        """Executes a command in the remote host's given CLI mode.

        Arguments:
          device_name: A string, the host to execute the command on.
          command: A string, the command to execute.
          mode: A string, the device mode ('shell' is the default and
            equivalent to None).
          callback: A callable to be called with the request object when
            the request is complete.
          callback_args: A tuple of positional arguments for the callback.
          callback_kwargs: A dict of keyword arguments for the callback.

        Returns:
          The command request result, if callback is None.
          None, if callback is None; callback will be run when the request
          completes.
        """
        request = Request('command', {'device_name': device_name,
                                      'command': command, 'mode': mode},
                          callback=callback, callback_args=callback_args,
                          callback_kwargs=callback_kwargs)
        r = self.exec_request(request)
        if request.callback:
            return
        else:
            if isinstance(r.error, Exception):
                raise r.error
            else:
                return r.result

    def devices_matching(self, regexp, callback=None, callback_args=None,
                         callback_kwargs=None):
        """Query the agent for a list of device names matching the regexp.

        Arguments:
          regexp: A string, the regular expression to use for matching.

        Returns:
          A list (possibly empty) of device names matching the expression.
        """
        request = Request('devices_matching', {'regexp': regexp},
                          callback=callback, callback_args=callback_args,
                          callback_kwargs=callback_kwargs)
        r = self.exec_request(request)
        if request.callback:
            return
        else:
            if isinstance(r.error, Exception):
                raise r.error
            else:
                return r.result

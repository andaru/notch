#!/usr/bin/env python
#
# Copyright 2010 Andrew Fort. All Rights Reserved.

"""The Notch Python client library.

This library implements the Notch Python API. Developers wishing to
create Notch applications will import and use this module.
"""

import eventlet
# Required for xmlrpclib/jsonrpclib.
eventlet.monkey_patch(all=True)

import logging
import os

import jsonrpclib

import lb_transport


# Use at most this number of green threads. Default also influenced by
# setting NOTCH_CONCURRENCY environment variable.
DEFAULT_NOTCH_CONCURRENCY = 1000


# Error classes.

class Error(Exception):
    pass


class NoAgentsError(Error):
    """No agent addresses were passed to the client."""

    
class NoCallbackError(Error):
    """The client got an response for a request but has no callback to run."""


class UnknownCommandError(Error):
    """The request contained an unknown command."""


class NotchRequest(object):
    """An object containing a Notch request (and response).

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
    """

    def __init__(self, notch_method, arguments=None,
                 callback=None, callback_args=None, callback_kwargs=None):
        # Request arguments.
        self.notch_method = notch_method
        self.arguments = arguments
        self.callback = callback
        self.callback_args = callback_args or tuple()
        self.callback_kwargs = callback_kwargs or {}
        # Response attributes.
        self.result = None
        self.error = None
        # Timers available for debugging.
        self.time_sent = None
        self.time_completed = None
        self.time_elapsed_s = None

    valid = property(lambda x: (x.notch_method and x.arguments))
    completed = property(lambda x: (x.result is not None or
                                    x.error is not None))


class NotchClient(object):
    """The Notch client object.

    After creating a Client instance, you call Notch API methods and
    provide callbacks to receive the results after the I/O operations
    complete.

    Example:
      import notch.client
      c = notch.client.NotchClient('localhost:8800')
      req = notch.client.NotchRequest('command', {'device_name': 'ar1.foo',
                                                  'command': 'show ver'})
      ar1_show_ver_output = c.exec_request(req)

    Asynchronous operation is possible, see the callback* attributes
    on the NotchRequest object (and the keyword arguments for the
    exec_request method here).
      
    Attributes:
      agents: An iterable of strings, host:port pairs for Notch Agents.
        Also accepts a string for a single agent host:port pair.
      max_concurrency: An int, maximum number of concurrent requests to make.
      path: The URL to access the Notch RPC endpoint on all agents.
    """

    def __init__(self, agents, max_concurrency=None,
                 path='/services/notch.jsonrpc',
                 use_ssl=False):
        """Initializer.

        Arguments:
          use_ssl: A boolean, if True, use HTTPS.

        Raises:
          NoAgentsError: If no agents were supplied.
        """
        if isinstance(agents, str):
            self.agents = [agents]
        else:
            self.agents = agents
        self.max_concurrency = (max_concurrency or
                                os.getenv('NOTCH_CONCURRENCY') or
                                DEFAULT_NOTCH_CONCURRENCY)
        self.path = path
        if use_ssl:
            self._protocol = 'https://'
        else:
            self._protocol = 'http://'

        self._pool = eventlet.greenpool.GreenPool(self.max_concurrency)
        self._notch = None
        self._transport = None
        self._setup_agents()

    def _setup_agents(self):
        """Sets up the Notch JSON RPC agent connection.

        Raises:
          NoAgentsError: If no agents were supplied.
        """
        if not self.agents:
            raise NoAgentsError('No Notch agents supplied to Client.')
        else:
            self._transport = lb_transport.LoadBalancingTransport(
                hosts=self.agents, transport=jsonrpclib.Transport)
            self._notch = jsonrpclib.ServerProxy(
                self._protocol + str(self.path), transport=self._transport)

    def _exec_request_callback(self, gt, *args, **kwargs):
        """Asynchronously receives responses and runs the user callback.

        Arguments:
          gt: A GreenThread, the thread that completed.
          args: Tuple of arguments for the user callback.
          kwargs: Dict of keyword arguments for the user callback.

        Raises:
          NoCallbackError: The request had no callback.
        """
        # wait() returns immediately as we have been called.
        value = gt.wait()
        if value is not None:
            request, result = value
            request.result = result
            if request.callback is not None:
                request.callback(request, *args, **kwargs)
            else:
                raise NoCallbackError(
                    'Asynchronous mode used without defined callback.')

    def exec_request(self, request, callback=None, args=None, kwargs=None):
        """Executes a NotchRequest in this client.

        Arguments:
          request: A NotchRequest to execute.
          callback: None or a callable. If not None, uses asynchronous mode,
            calling the callback with request, *args and **kwargs as arguments.
          args: Tuple of arguments for the user callback.
          kwargs: Dict of keyword arguments for the user callback.

        Returns:
          If the request has no callbacks, the request's result will be
          returned. If there is a callback, None is returned.
        """
        if callback: request.callback = callback
        if args: request.callback_args = args
        if kwargs: request.callback_kwargs = kwargs
        method = getattr(self, '_' + request.notch_method, None)

        if method is not None:
            gt = self._pool.spawn(method, request)
        else:
            raise UnknownCommandError('%r is not a Notch command.'
                                      % request.notch_method)
        if request.callback is None:
            # Sync: blocks our caller until the result arrives.
            request, result = gt.wait()
            return result
        else:
            # Async: call the user's callback upon completion.
            gt.link(self._exec_request_callback,
                    *request.callback_args, **request.callback_kwargs)

    def _command(self, request):
        """Executes a command in the remote host's given CLI mode."""
        try:
            result = self._notch.command(
                device_name=request.arguments.get('device_name', None),
                command=request.arguments.get('command', None),
                mode=request.arguments.get('mode', None))
        except Exception, e:
            logging.error('Exception <%s> during Notch method: %s',
                          str(e.__class__), str(e))
            return None
        else:
            return (request, result)

    def wait_all(self):
        """Waits for all outstanding requests to complete.

        Useful when running a client without a user interface.
        """
        self._pool.waitall()

    num_requests_running = property(lambda x: x._pool.running())
    num_requests_waiting = property(lambda x: x._pool.waiting())

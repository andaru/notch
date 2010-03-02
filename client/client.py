#!/usr/bin/env python
"""
The Notch Python client library.

This library implements the Notch Python API. Developers wishing to
create Notch applications will import and use this module.
"""


import eventlet
from eventlet.green import time
from eventlet.green import socket
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


class UnknownCommandError(Error):
    """The request contained an unknown command."""


class NotchRequest(object):
    """An object containing the Notch Request and Response."""

    def __init__(self, command, arguments,
                 callback=None, callback_args=None, callback_kwargs=None):
        self.command = command
        self.result = None
        self.arguments = arguments
        self.callback = callback
        self.callback_args = callback_args or tuple()
        self.callback_kwargs = callback_kwargs or {}


class Client(object):
    """The Notch client object.

    After creating a Client instance, you call Notch API methods and
    provide callbacks to receive the results after the I/O operations
    complete.

    Attributes:
      agents: An iterable of strings, host:port pairs for Notch Agents.
        Also accepts a string for a single agent host:port pair.
      max_concurrency: An int, the maximum number of concurrent activities.
      path: The URL to access the Notch RPC endpoint on all agents.
    """

    def __init__(self, agents, max_concurrency=None,
                 path='/services/notch.jsonrpc'):
        """Initializer.

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
        self._pool = eventlet.greenpool.GreenPool(self.max_concurrency)
        self._notch = None
        self._transport = None
        self._setup_agents()

    def _setup_agents(self):
        if not self.agents:
            raise NoAgentsError('No Notch agents supplied to Client.')
        else:
            self._transport = lb_transport.LoadBalancingTransport(
                hosts=self.agents, transport=jsonrpclib.Transport)
            self._notch = jsonrpclib.ServerProxy('http://.' + str(self.path),
                                                 transport=self._transport)

    def _exec_request_callback(self, gt, *args, **kwargs):
        # wait() returns immediately as we have been called.
        value = gt.wait()
        if value is not None:
            request, result = value
            request.result = result
            request.callback(request, *args, **kwargs)
        
    def exec_request(self, request, callback=None, args=None, kwargs=None):
        """Executes a NotchRequest in this client, sync or async."""
        if callback:
            request.callback = callback
        if args:
            request.callback_args = args
        if kwargs:
            request.callback_kwargs = kwargs
        method = getattr(self, '_' + request.command, None)

        if method is not None:
            gt = self._pool.spawn(method, request)
        else:
            raise UnknownCommandError('%r is not a Notch command.'
                                      % request.command)
        if request.callback is None:
            # Sync: blocks our caller until the result arrives.
            return gt.wait()
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
    

# test

def test_print_result(request, *args, **kwargs):
    print request.result


if __name__ == '__main__':
    cl = Client('localhost:8800')
    r = NotchRequest('command',
                     {'mode': 'shell',
                      'device_name': 'localhost',
                      'command': 'banner krad'}, callback=test_print_result)
    cl.exec_request(r)
    # Wait for all requests to finish before exiting.
    cl.wait_all()

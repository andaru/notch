#!/usr/bin/env python
"""
A load-balancing xmlrpclib Transport proxy.

Using the LoadBalancingChannel class as the transport keyword argument
to an xmlrpclib (or jsonrpclib) proxy causes requests to be sent to
all avaliable backends.

Differing load-balancer strategies can be created by sub-classing this
and over-riding the next_channel method, and initializer to carry additional
data structures that needed during the life of the channel.
"""

import collections
import socket
import threading
import xmlrpclib


# Backend RPC server states.
IDLE = 0
ACTIVE = 1
CONNECTED = 2
ERROR = 3


class BackEnd(object):
    """Stores information about an individual back end worker.
    
    Attributes:
      address: A host[:port] string to reach the back-end.
      handler_uri: A URI string, the path to the RPC handler.
      num_rpc_inflight: An int, the number of RPCs currently outstanding.
      state: An int, one of the module constants IDLE, ACTIVE, CONNECTED, ERROR.
      transport: An xmlrpclib.Transport subclass, the RPC Transport class
        to use for this back end.
    """
    
    def __init__(self, address=None, handler_uri=None, transport=None):
        self._address = address
        self.handler_uri = handler_uri
        self.num_rpc_inflight = 0
        self.state = IDLE
        self.connection = None
        self._transport_obj = transport
        self.transport = None
        self._setup_transport()
    
    def _setup_transport(self):
        try:
            self.transport = self._transport_obj()
            self.transport.user_agent += ' (load_balanced_task)'
            self.state = ACTIVE
        finally:
            return
    
    def _set_address(self, a):
        self._address = a
        self._setup_transport()
    
    address = property(lambda cls: cls._address, _set_address)



class LoadBalancingTransport(xmlrpclib.Transport):
    """A load-balancing RPC transport.
    
    Attributes:
      hosts: Sequence of strings, host[:port] addresses to connect to.
      transport: The transport class used for all back end connections.
    """
    
    def __init__(self, use_datetime=0, hosts=None, transport=None):
        xmlrpclib.Transport.__init__(self, use_datetime=use_datetime)
        self.hosts = hosts or set()
        self._transport_obj = transport or xmlrpclib.Transport
        self._backends = set()
        # -1 is also a stop sentinel, once started. sequential advancing.
        self._call_number = -1
        self._backends_in = {}
        self._setup_backends()
        self._started = False
        self._current_backend = None
    
    def _host_form(self, hostport):
        if ':' in hostport:
            return hostport[:hostport.find(':')]
        else:
            return hostport
    
    def _next_backend(self):
        if self._call_number == -1 and not self._started:
            self._started = True
            self._call_number = 0
        elif self._call_number == -1 and self._started:
            self._started = False
        
        self._call_number %= len(self._backends)
        try:
            try:
                return sorted(list(self._backends))[self._call_number]
            except IndexError:
                return sorted(list(self._backends))[len(self._backends)]
        finally:
            self._call_number += 1
    
    def _setup_backends(self):
        self._backends = set()
        for host in self.hosts:
            self._backends.add(BackEnd(address=host,
                                       transport=self._transport_obj))
        self._update_backend_map()
    
    def _update_backend_map(self):
        for backend in self._backends:
            if backend.state in self._backends_in:
                self._backends_in[backend.state] += 1
            else:
                self._backends_in[backend.state] = 1
    
    def request(self, host, handler, request_body, verbose=0):
        exc = None
        for _ in xrange(len(self._backends)):
            self._current_backend = self._next_backend()
            try:
                response = self._current_backend.transport.request(
                    self._current_backend.address, handler, request_body,
                    verbose=verbose)
                exc = None
                return response
            except Exception, e:
                exc = e
                continue
        if exc:
            raise exc
    
    def send_host(self, connection, unused_host):
        connection.putheader('Host', self._host_form(self._current_backend))

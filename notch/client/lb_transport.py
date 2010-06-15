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

"""A load-balancing xmlrpclib Transport proxy class.

Using the LoadBalancingChannel class as the transport keyword argument
to an xmlrpclib (or jsonrpclib) proxy causes requests to be sent to
all avaliable backends.

Differing load-balancer strategies can be created by sub-classing this
and over-riding the next_channel method, and initializer to carry additional
data structures that needed during the life of the channel.
"""

import collections
import copy
import random
import socket
import sys
import threading
import time
import xmlrpclib


# Backend RPC server states.
IDLE = 0
ACTIVE = 1
CONNECTED = 2
ERROR = 3


class Backend(object):
    """Stores information about an individual back end worker.

    Attributes:
      address: A host[:port] string to reach the back-end.
      handler_uri: A URI string, the path to the RPC handler.
      num_rpc_inflight: An int, the number of RPCs outstanding.
      state: An int, one of the module state constants.
      transport: The xmlrpclib.Transport subclass to use as transport.
    """

    def __init__(self, address=None, handler_uri=None, transport=None):
        self._address = address
        self.handler_uri = handler_uri
        self.num_rpc_inflight = 0
        self.state = IDLE
        self.transport = None
        self._transport_obj = transport
        self._setup_transport()

    def _set_transport_obj(self, t):
        self._transport_obj = t
        self._setup_transport()

    def _setup_transport(self):
        try:
            self.transport = self._transport_obj()
            self.state = ACTIVE
        finally:
            return

    def _set_address(self, a):
        self._address = a
        self._setup_transport()

    def __repr__(self):
        return '%s(address=%r, num_rpc_inflight=%r)' % (
            self.__class__.__name__, self._address, self.num_rpc_inflight)

    address = property(lambda cls: cls._address, _set_address)
    transport_obj = property(lambda cls: cls._transport_obj)
    


class BackendPolicy(object):
    """A load-balancing policy for a group of RPC back-ends.

    Subclasses define a generator, named backend_stream(),
    based on the desired load-balancing policy. This generator will
    yield Backend objects, with each iteration being a new incoming request.

    Note that since the backends are iterated over, the set of backends
    cannot be changed after the object is created.
    """

    def __init__(self, hosts):
        """Initializer.

        Args:
          hosts: An iterable of back end host name:port pairs.
        """
        self._lock = threading.Lock()
        self._backends = frozenset(hosts)
        self.error_requests = {}
        self.total_requests = {}
        self.response_sizes = {}
        self.last_request_rtt = {}
        self._last_request_start = {}
        self._setup_backends()

    def __iter__(self):
        for backend in self.backend_stream():
            self.total_requests[backend] += 1
            self._last_request_start[backend] = time.time()
            yield backend
        
    def _setup_backends(self):
        for backend in self._backends:
            self.total_requests[backend] = 0
            self.error_requests[backend] = 0
            self.response_sizes[backend] = 0
            self.last_request_rtt[backend] = 0
        self.setup_policy()

    def setup_policy(self):
        """Perform any variable definition and policy setup here."""
        pass

    def backend_stream(self):
        """A generator that eternally yields the next Backend to use."""
        raise NotImplementedError

    def report_response(self, backend, response, exc):
        # XXX necessary? test for removal of backends to confirm.
        if backend not in self._backends:
            return
        self._lock.acquire()
        try:
            if exc is not None:
                self.error_requests[backend] += 1
            elif response is not None:
                self.response_sizes[backend] += len(response)
            else:
                # response and exc are None, meaning there was an error.
                backend.state = ERROR
            start = self._last_request_start[backend]
            self.last_request_rtt[backend] = max(0, time.time() - start)
        finally:
            self._lock.release()
        backend.num_rpc_inflight -= 1

    backends = property(lambda cls: cls._backends)  


class RandomPolicy(BackendPolicy):
    """A back-end policy that randomly selects the next Backend."""

    def backend_stream(self):
        while True:
            yield random.choice(list(self._backends))


class RoundRobinPolicy(BackendPolicy):
    """A round-robin back-end policy."""

    def backend_stream(self):
        while True:
            for backend in self._backends:
                yield backend


class LowestLatencyPolicy(BackendPolicy):
    """A policy that chooses the backend with the lowest request latency."""

    def _backend_up(self, backend_tuple):
        return (backend_tuple[1].state == ACTIVE
                or backend_tuple[1].state == IDLE)
    
    def backend_stream(self):
        while True:
            choice = None
            untimed_backends = ([(n, be) for (be, n)
                                 in self.last_request_rtt.iteritems()
                                 if n == 0])
            untimed_backends = filter(self._backend_up, untimed_backends)
            if untimed_backends:
                # Choose randomly until we have sufficient RTT data.
                choice = random.choice(list(self._backends))
            else:
                current_rtt = sorted([(n, be) for (be, n)
                                      in self.last_request_rtt.iteritems()])
                choice = current_rtt[0][1]
            yield choice


class LoadBalancingTransport(xmlrpclib.Transport):
    """A load-balancing RPC transport.

    This transport is not thread-safe, but not inherently unsafe.

    Attributes:
      hosts: Sequence of strings, host[:port] addresses to connect to.
      transport: Transport class used for each task.
    """

    # Our default choice of policy.
    DEFAULT_POLICY = LowestLatencyPolicy

    def __init__(self, use_datetime=0, hosts=None, transport=None, policy=None):
        xmlrpclib.Transport.__init__(self, use_datetime=use_datetime)
        self._hosts = hosts
        self.will_retry = False
        self._transport_obj = transport or xmlrpclib.Transport
        self._setup_backends()
        # Finally, get the policy up.
        if policy is None:
            self.policy = self.DEFAULT_POLICY(self._backends)
        else:
            self.policy = policy(self._backends)
        if self._hosts is None:
            raise ValueError('%s cannot be created with no backend hosts.',
                             self.__class__.__name__)

    def _setup_backends(self):
        self._backends = set()
        for host in self._hosts:
            self._backends.add(Backend(address=host,
                                       transport=self._transport_obj))

    def request(self, host, handler, request_body, verbose=False):
        # TODO(afort): Handle ECONNREFUSED even in no-retry mode.
        exc = None
        backend = iter(self.policy).next()

        result = exc = None
        if not self.will_retry:
            try:
                backend.num_rpc_inflight += 1
                result = backend.transport.request(
                    backend.address, handler, request_body, verbose=verbose)
            except Exception, e:
                exc = e
            self.policy.report_response(backend, result, exc)
            if exc:
                raise exc
            else:
                return result
        else:
            raise NotImplementedError('Non fail-fast mode not yet implemented.')

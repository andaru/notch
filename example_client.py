#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Super basic notch test."""

# Get jsonrpclib from google code hosting.
import jsonrpclib

import multirpc

lb_transport = multirpc.LoadBalancingTransport(
    hosts=['localhost:8800', 'localhost:8889', 'localhost:8890'],
    transport=jsonrpclib.Transport)

# Multirpc doesn't care about the hostname in the URL below, since it's
# supplied above.
notch = jsonrpclib.Server('http://x/services/notch.jsonrpc',
                           transport=lb_transport)

print notch.command(device_name='localhost',
                    command='ls', mode='shell')

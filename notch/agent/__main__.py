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

"""Notch Agent in Tornado Server mode."""

import eventlet

# XXX monkey-patching os causes a deadlock.
eventlet.monkey_patch(all=False, os=False, socket=True, select=True)


import logging
import socket

import tornado.httpserver
import tornado.ioloop

import applications
import handlers
import errors

import utils


if __name__ == '__main__':
    configuration, port = utils.get_config_port_tornado()
    try:
        application = applications.NotchTornadoApplication(configuration)
        server = tornado.httpserver.HTTPServer(application)
        server.listen(port)
        logging.debug('Starting HTTP server on port %d', port)
        tornado.ioloop.IOLoop.instance().start()
        tornado.ioloop.IOLoop.instance().stop()
        raise SystemExit(0)
    except socket.error, e:
        logging.error('Could not listen on port %d: %s', port, e)
        raise SystemExit(2)
    except TypeError, e:
        logging.error('Invalid port: %r', port)
        raise SystemExit(2)
    except errors.Error, e:
        logging.error(str(e))
        raise SystemExit(1)
    except KeyboardInterrupt:
        print

        handlers.StopHandler.stop()

        logging.warn('Server shutdown by keyboard interrupt')
        raise SystemExit(3)

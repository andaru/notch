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

"""Notch Agent."""

import logging
import socket

import tornado.options
import tornado.httpserver
import tornado.ioloop

import agent
import handlers
import notch_config


tornado.options.define('port', default=None,
                       help='Run on the given port', type=int)
tornado.options.define('config', default='notch.yaml',
                       help='Notch configuration file', type=str)

DEFAULT_PORT = 8888


def load_config(config_path):
    try:
        config = notch_config.get_config_from_file(config_path)
    except notch_config.ConfigMissingRequiredSectionError, e:
        logging.error('Config file %r did not parse a section named: %r',
                      tornado.options.options.config, str(e))
        raise
    if not config:
        raise notch_config.Error('No configuration was loaded.')
    else:
        return config


def determine_port(options):
    if options:
        return (tornado.options.options.port or
                options.get('port') or
                DEFAULT_PORT)
    else:
        return tornado.options.options.port or DEFAULT_PORT


def create_application():
    try:
        tornado.options.parse_command_line()
        logging.debug('Loading configuration from file %r',
                      tornado.options.options.config)
        configuration = load_config(tornado.options.options.config)
    except (tornado.options.Error, notch_config.Error), e:
        logging.error(str(e))
        return 1
    else:
        application = NotchApplication(configuration)
        return application


if __name__ == '__main__':
    try:
        tornado.options.parse_command_line()
        logging.debug('Loading configuration from file %r',
                      tornado.options.options.config)
        configuration = load_config(tornado.options.options.config)
    except (tornado.options.Error, notch_config.Error), e:
        logging.error(str(e))
        raise SystemExit(1)

    port = determine_port(configuration.get('options'))

    try:
        application = agent.NotchTornadoApplication(configuration)
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
    except notch_config.Error, e:
        logging.error(str(e))
        raise SystemExit(1)
    except KeyboardInterrupt:
        print

        handlers.StopHandler.stop()

        logging.warn('Server shutdown by keyboard interrupt')
        raise SystemExit(3)

else:
    tornado.options.parse_command_line()
    logging.debug('Configuring WSGI application from file %r',
                  tornado.options.options.config)
    configuration = load_config('/Users/afort/Projects/notch/notch.yaml')
    wsgi_application = agent.NotchWSGIApplication(configuration)

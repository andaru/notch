#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Notch Agent binary.

This binary is run to start the Notch Agent, which uses the Tornado
web-server along with the TornadoRPC JSON/XML-RPC library to offer
the Notch server API to Notch clients (via HTTP/JSON-RPC).
"""

import logging
import re
import socket
import threading
import sys
import time

import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.options
import tornado.web
import tornadorpc.json

import controller
import handlers
import notch_config


tornado.options.define('port', default=None,
                       help='Run on the given port', type=int)
tornado.options.define('config', default='notch.yaml',
                       help='Notch configuration file', type=str)

DEFAULT_PORT = 8888


class NotchApplication(tornado.web.Application):

    def __init__(self, configuration):
        urls = [
            (r'/', handlers.HomeHandler),
            (r'/_threads', handlers.ThreadsHandler),
            (r'/services/notch.jsonrpc', handlers.NotchJsonRpcHandler),
            (r'/stopstopstop', handlers.StopHandler)]
        control = controller.Controller(configuration)
        settings = dict(controller=control)
        tornado.web.Application.__init__(self, urls, **settings)


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


def main():
    try:
        tornado.options.parse_command_line()
        logging.debug('Loading configuration from file %r',
                      tornado.options.options.config)
        configuration = load_config(tornado.options.options.config)
    except (tornado.options.Error, notch_config.Error), e:
        logging.error(str(e))
        return 1

    port = determine_port(configuration.get('options'))

    try:
        server = tornado.httpserver.HTTPServer(NotchApplication(configuration))
        server.listen(port)
    except socket.error, e:
        logging.error('Could not listen on port %d. %s', port, e)
        return 2
    except TypeError, e:
        logging.error('Invalid port: %r', port)
        return 2
    except notch_config.Error, e:
        logging.error(str(e))
        return 1

    try:
        logging.debug('Starting HTTP server on port %d', port)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print
        handlers.StopHandler.stop()
        logging.warn('Server shutdown by keyboard interrupt')
        return 3

    tornado.ioloop.IOLoop.instance().stop()
    return 0


if __name__ == '__main__':
    result = main()
    sys.exit(result)

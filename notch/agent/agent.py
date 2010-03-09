#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Notch Agent binary.

This binary is run to start the Notch Agent, which uses the Tornado
web-server along with the TornadoRPC JSON/XML-RPC library to offer
the Notch server API to Notch clients (via HTTP/JSON-RPC).
"""

import eventlet
eventlet.monkey_patch(all=False, os=False, socket=True, select=True)

import logging
import re
import socket

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.wsgi
import tornadorpc.json

import controller
import handlers
import notch_config


tornado.options.define('port', default=None,
                       help='Run on the given port', type=int)
tornado.options.define('config', default='notch.yaml',
                       help='Notch configuration file', type=str)

DEFAULT_PORT = 8888


class NotchBaseApplication(object):

    urls = [(r'/', handlers.HomeHandler),
            (r'/_threads', handlers.ThreadsHandler),
            (r'/stopstopstop', handlers.StopHandler)]


class NotchTornadoApplication(tornado.web.Application):

    def __init__(self, configuration):
        urls = NotchBaseApplication.urls + [
            (r'/services/notch.jsonrpc', handlers.NotchAsyncJsonRpcHandler)]
        self.controller = controller.Controller(configuration)
        eventlet.spawn_n(self.controller.run_maintenance)
        settings = dict(controller=self.controller)
        tornado.web.Application.__init__(self, urls, **settings)


class NotchWSGIApplication(tornado.wsgi.WSGIApplication):

    def __init__(self, configuration):
        urls = NotchBaseApplication.urls + [
            (r'/services/notch.jsonrpc', handlers.NotchSyncJsonRpcHandler)]
        self.controller = controller.Controller(configuration)
        eventlet.spawn_n(self.controller.run_maintenance)
        settings = dict(controller=self.controller)
        tornado.wsgi.WSGIApplication.__init__(self, urls, **settings)


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
        application = NotchTornadoApplication(configuration)
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
    wsgi_application = NotchWSGIApplication(configuration)

#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

import eventlet
eventlet.monkey_patch(all=False, os=False, socket=True, select=True)

import tornado.web
import tornado.wsgi

import controller
import handlers


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


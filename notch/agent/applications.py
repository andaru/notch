#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.
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

"""Notch Agent application classes."""

import eventlet

import tornado.web
import tornado.wsgi

import controller
import handlers


# URLs for common pages.
BASE_URLS = [(r'/', handlers.HomeHandler),
             (r'/stopstopstop', handlers.StopHandler)]

# The JSON-RPC v2.0 interface.
JSON_RPC2_URL = r'/JSONRPC2'


class NotchTornadoApplication(tornado.web.Application):

    def __init__(self, configuration):
        urls = BASE_URLS + [
            (JSON_RPC2_URL, handlers.NotchSyncJsonRpcHandler)]
        # Initialise the controller and start the maintenance task.
        self.controller = controller.Controller(configuration)
        eventlet.spawn_n(self.controller.run_maintenance)

        settings = dict(controller=self.controller)
        tornado.web.Application.__init__(self, urls, **settings)


class NotchWSGIApplication(tornado.wsgi.WSGIApplication):

    def __init__(self, configuration):
        urls = BASE_URLS + [
            (JSON_RPC2_URL, handlers.NotchSyncJsonRpcHandler)]
        # Initialise the controller and start the maintenance task.
        self.controller = controller.Controller(configuration)
        eventlet.spawn_n(self.controller.run_maintenance)

        settings = dict(controller=self.controller)
        tornado.wsgi.WSGIApplication.__init__(self, urls, **settings)

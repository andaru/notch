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

"""Notch Request Handlers.

These handlers implement the server-side API using session and device
objects, using the Tornado request handler framework.
"""

import logging
import traceback

import jsonrpclib
# Disable automatic class translation.
jsonrpclib.config.use_jsonclass = False

import tornado.ioloop
import tornado.options
import tornado.web
import tornadorpc.json
import tornadorpc.base

import notch.agent.errors


class BaseHandler(tornado.web.RequestHandler):
    """Base class for common request handler functionality."""


class HomeHandler(BaseHandler):
    """Handles the root page."""


class SynchronousJSONRPCHandler(tornadorpc.json.JSONRPCHandler):
    _RPC = tornadorpc.json.JSONRPCParser(jsonrpclib)

    def post(self):
        self._RPC.faults.codes.update(notch.agent.errors.error_dictionary)
        self.controller = self.settings['controller']
        super(SynchronousJSONRPCHandler, self).post()


#pylint: disable-msg=E1101
class NotchAPI(object):
    """The Notch API.  Used as a mix-in."""
    _RPC = tornadorpc.json.JSONRPCParser(jsonrpclib)

    def handle_exception(self, exc):
        # We get _RPC_ attribute via mixin.
        if not isinstance(exc, notch.agent.errors.ApiError):
            logging.debug(traceback.format_exc())
        return notch.agent.errors.rpc_error_handler(exc, self._RPC)

    def devices_matching(self, **kwargs):
        try:
            if not kwargs:
                return
            else:
                arg = kwargs.get('regexp', '^$')
                return list(
                    self.controller.device_manager.devices_matching(arg))
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def devices_info(self, **kwargs):
        try:
            if not kwargs:
                return
            else:
                arg = kwargs.get('regexp', '^$')
                result = {}
                devices = self.controller.device_manager.devices_matching(arg)
                for d in devices:
                    dev_info = self.controller.device_manager.device_info(d)
                    if dev_info is None:
                        continue
                    if isinstance(dev_info.addresses, list):
                        add = dev_info.addresses
                    else:
                        add = [dev_info.addresses]
                    result[d] = {'device_type': dev_info.device_type,
                                 'addresses': add}
                return result
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def command(self, **kwargs):
        try:
            return self.controller.request('command', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def get_config(self, **kwargs):
        try:
            return self.controller.request('get_config', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def set_config(self, **kwargs):
        try:
            return self.controller.request('set_config', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def copy_file(self, **kwargs):
        try:
            return self.controller.request('copy_file', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def upload_file(self, **kwargs):
        try:
            return self.controller.request('upload_file', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def download_file(self, **kwargs):
        try:
            return self.controller.request('download_file', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def delete_file(self, **kwargs):
        try:
            return self.controller.request('delete_file', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def lock(self, **kwargs):
        try:
            return self.controller.request('lock', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)

    def unlock(self, **kwargs):
        try:
            return self.controller.request('unlock', **kwargs)
        except notch.agent.errors.ApiError, e:
            return self.handle_exception(e)
#pylint: enable-msg=E1101


class NotchSyncJsonRpcHandler(NotchAPI, SynchronousJSONRPCHandler):
    """The Notch API as presented to JSON-RPC asynchronously, for WSGI."""


class StopHandler(tornado.web.RequestHandler):
    """Request handler used to stop the Notch agent."""

    def get(self):
        logging.warn('Shutdown requested via HTTP server.')
        self.stop()

    def post(self):
        return self.get()

    @classmethod
    def stop(cls):
        tornado.ioloop.IOLoop.instance().stop()

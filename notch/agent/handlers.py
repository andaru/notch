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

import cgi
import functools
import inspect
import logging
import pprint
import sys
import thread
import threading
import time
import traceback

import jsonrpclib

import tornado.ioloop
import tornado.options
import tornado.web
import tornadorpc.json
import tornadorpc.base

import errors
import tp


tornado.options.define('threadpool_num_threads', default=64,
                       help='Number of threads to use in sync task threadpool.',
                       type=int)


# A threadpool used for synchronous tasks.
_tp = tp.ThreadPool(tornado.options.options.threadpool_num_threads)


class BaseHandler(tornado.web.RequestHandler):
    """Base class for common request handler functionality."""


class HomeHandler(BaseHandler):
    """Handles the root page."""


class ThreadsHandler(BaseHandler):
    """Handles /_threads."""

    def get(self):
        self.set_header('Content-Type', 'Text/HTML')
        table_head = ['<table>']
        table_foot = ['</table>']
        foot = ['</body></html>']
        output = ['<html><head>']
        head_end = ['</head><body>']
        style = ['<style type="text/css">',
                 '.code { font-family: monospace; }',
                 '.heavy { font-weight: bold; }',
                 '</style>']
        output.extend(style)
        output.extend(head_end)

        globals_done = False
        for f in sys._current_frames().itervalues():
            if not globals_done:
                output.append('<div>')
                output.extend(table_head)
                for k, v in f.f_globals.iteritems():
                    if k.startswith('__'): continue
                    output.append(
                        '<tr><td class="heavy">%s</td><td class="code">%s</td>'
                        % (cgi.escape(pprint.pformat(k)[1:-1]),
                           cgi.escape(pprint.pformat(v)[1:-1])))

                output.extend(table_foot)
                output.append('</div>')
                globals_done = True

                output.append('<p>Thread objects')
                output.extend(table_head)
                threads = ['<tr><td class="heavy">Name</td><td class="heavy">'
                           'Identifier</td></tr>']
                for t in threading.enumerate():
                    ident = str(t.ident)
                    if t.ident is None:
                        ident = '(not started)'

                    threads.append('<tr><td class="heavy">%s</td>'
                                   '<td class="code"><code>%s</code></td>'
                                   % (cgi.escape(t.name), cgi.escape(ident)))
                output.extend(threads)
                output.extend(table_foot)

            source_lines, n_lines = inspect.getsourcelines(f.f_code)
            code = ['<hr />']
            if source_lines:
                code.append('%s lines of source' % len(source_lines))

            code.extend(table_head)
            for i in xrange(n_lines, len(source_lines)):
                code.append('<tr><td>%s</td><td class="code">%s</td></tr>'
                            % (cgi.escape(str(i)),
                               cgi.escape(str(source_lines[i-n_lines]))))
            code.extend(table_foot)
            output.extend(code)


            output.extend(table_head)
            locals = []
            for k, v in f.f_locals.iteritems():
                if 'globals_done' == k:
                    locals = []
                    break
                locals.append('<tr><td class="heavy">%s</td><td>%s</td>'
                              % (cgi.escape(str(k)), cgi.escape(str(v))))

            output.extend(locals)
            output.extend(table_foot)



            output.extend(foot)
        self.write(' '.join(output))


class Faults(tornadorpc.base.Faults):

    codes = tornadorpc.base.Faults.codes.copy().update(errors.error_dictionary)


class NotchJsonRpcParser(tornadorpc.json.JSONRPCParser):

    @property
    def faults(self):
        return Faults(self)


class AsynchronousJSONRPCHandler(tornadorpc.base.BaseRPCHandler):
    _RPC_ = tornadorpc.json.JSONRPCParser(jsonrpclib)

    def _execute_rpc(self, request_body):
        """Executes the RPC and sets the RPC response."""
        response_data = self._RPC_.run(self, request_body)
        self.set_header('Content-Type', self._RPC_.content_type)
        self.write(response_data)
        self.finish()

    @tornado.web.asynchronous
    def post(self):
        """Multi-threaded JSON-RPC POST handler."""
        self.controller = self.settings['controller']
        _tp.put(self._execute_rpc, self.request.body)

    
class SynchronousJSONRPCHandler(tornadorpc.base.BaseRPCHandler):
    _RPC_ = tornadorpc.json.JSONRPCParser(jsonrpclib)
      
    def post(self):
        """Single-threaded JSON-RPC POST handler."""
        self.controller = self.settings['controller']
        response_data = self._RPC_.run(self, self.request.body)
        self.set_header('Content-Type', self._RPC_.content_type)
        self.write(response_data)
        self.finish()


#pylint: disable-msg=E1101
class NotchAPI(object):
    """The Notch API."""

    def handle_exception(self, exc):
        # TODO(afort): Add specific error codes in errors.py
        logging.error('%s: %s', exc.__class__.__name__, str(exc))
        # We get _RPC_ attribute via mixin.
        return self._RPC_.faults.internal_error(str(exc))

    def devices_matching(self, *args):
        try:
            if not args:
                return
            else:
                return self.controller.devices_matching(args[0])
        except errors.ApiError, e:
            return self.handle_exception(e)

    def command(self, **kwargs):
        try:
            return self.controller.request('command', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)

    def get_config(self, **kwargs):
        try:
            return self.controller.request('get_config', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)

    def set_config(self, **kwargs):
        try:
            return self.controller.request('set_config', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)

    def copy_file(self, **kwargs):
        try:
            return self.controller.request('copy_file', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)

    def upload_file(self, **kwargs):
        try:
            return self.controller.request('upload_file', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)

    def download_file(self, **kwargs):
        try:
            return self.controller.request('download_file', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)

    def delete_file(self, **kwargs):
        try:
            return self.controller.request('delete_file', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)

    def lock(self, **kwargs):
        try:
            return self.controller.request('lock', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)

    def unlock(self, **kwargs):
        try:
            return self.controller.request('unlock', **kwargs)
        except errors.ApiError, e:
            return self.handle_exception(e)
#pylint: enable-msg=E1101


class NotchAsyncJsonRpcHandler(NotchAPI, AsynchronousJSONRPCHandler):
    """The Notch API as presented to JSON-RPC asynchronously, for Tornado."""


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

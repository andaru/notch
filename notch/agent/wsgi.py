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

"""Module carrying the initialised WSGI application.

If using a WSGI server that expects a module dotted path, refer to the
application using the path:

  notch.agent.wsgi.application

If using a Python Paste .ini style configuration, use this path:

XXX insert paste .ini-file config help here.

"""

import logging
import os

import applications
import utils


notch_config_path = os.getenv('NOTCH_CONFIG')


class NoConfigError(Exception):
    pass


if __name__ != '__main__':
    if not notch_config_path:
        msg = ('The Notch WSGI application requires the NOTCH_CONFIG\n'
               'environment variable to have the path to your config file.\n'
               'Example:\n'
               '  $ export NOTCH_CONFIG=/usr/local/etc/notch/notch.yaml')
        logging.error(msg)
        raise SystemExit(1)
    else:
        _configuration = utils.load_config(notch_config_path)
            # WSGI application object.
        application = applications.NotchWSGIApplication(_configuration)
        __all__ = ['application']

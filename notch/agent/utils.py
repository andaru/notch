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

"""Miscellaneous utility methods."""


import logging

import tornado.options

import errors
import notch_config

DEFAULT_PORT = 8080


tornado.options.define('port', default=None,
                       help='Run on the given port', type=int)
tornado.options.define('config', default='notch.yaml',
                       help='Notch configuration file', type=str)


def get_config_port_tornado():
    try:
        tornado.options.parse_command_line()
        logging.debug('Loading configuration from file %r',
                      tornado.options.options.config)
        configuration = load_config(tornado.options.options.config)
    except (errors.ConfigError, tornado.options.Error), e:
        logging.error(str(e))
        raise SystemExit(1)

    port = determine_port(configuration.get('options'))
    return configuration, port



def load_config(config_path):
    try:
        config = notch_config.get_config_from_file(config_path)
    except errors.ConfigMissingRequiredSectionError, e:
        logging.error('Config file %r did not parse a section named: %r',
                      tornado.options.options.config, str(e))
        raise
    if not config:
        raise errors.ConfigError('No configuration was loaded.')
    else:
        return config


def determine_port(options):
    if options:
        return (tornado.options.options.port or
                options.get('port') or
                DEFAULT_PORT)
    else:
        return tornado.options.options.port or DEFAULT_PORT

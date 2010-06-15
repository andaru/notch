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

"""Module carrying an application attribute suitable for use in mod_wsgi.

This module allows you to run Notch under Apache2/mod_wsgi, providing
debug logging (see LOG_FILENAME variable, below)

"""

import logging
import logging.handlers
import os
import site
import sys


# Set this to your Notch Agent virtualenv's site-packages directory.
VIRTUAL_ENVIRONMENT = '/usr/local/notch/venv/NOTCH/lib/python2.6/site-packages'

site.addsitedir(VIRTUAL_ENVIRONMENT)


import notch.agent.applications
import notch.agent.utils


__all__ = ['application']


# Shall we enable the extra logging?
ENABLE_EXTRA_LOGS = True

# Where to find the Notch (.yaml) configuration file.
NOTCH_CONFIG_PATH = '/usr/local/notch/notch.yaml'

# Where to write debug logs to.
LOG_FILENAME = '/var/log/apache2/app_notch.log'
# Debug log level.
LOG_LEVEL = logging.DEBUG
LOG_MAX_SIZE = 20 * 1048576
LOG_BACKUP_COUNT = 5

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
log_handler = logging.handlers.RotatingFileHandler(
    LOG_FILENAME,
    maxBytes=LOG_MAX_SIZE,
    backupCount=LOG_BACKUP_COUNT)

# I2010-06-10 10:30:00,183 foo.py:187|Connecting to ......  
formatter = logging.Formatter(
    "%(levelname)1.1s%(asctime)s %(module)s:%(lineno)d %(message)s")
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)


class NoConfigError(Exception):
    pass


# Configuration loaded from Notch YAML configuration file.
_configuration = notch.agent.utils.load_config(NOTCH_CONFIG_PATH)
# WSGI application object.
application = notch.agent.applications.NotchWSGIApplication(
    _configuration)



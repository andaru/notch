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

"""Credential (login) information and credentials store.

This module has classes for managing credentials, which are the information
used to login to a device. This includes usernames and passwords along with
any required SSH private keys.
"""

import cStringIO
import logging
import re

import yaml

import errors


class Credential(object):
    """A system credential.

    A credential is login information used by the agent to authenticate to
    a device. We consider the concept of an 'enable' password as well as
    an SSH private key data field. Aditionally, whether to automatically
    enable (for e.g., on Cisco IOS hosts) and which connection method
    to use for devices matching this credential are recorded.

    Attributes:
      regexp: The generated regular expression object for this credential.
      regexp_string: A string, the string used to form the regexp attribute.
      auto_enable: A boolean, whether the agent will attempt to enable.
      connect_method: A string, the connection method for this credential.
      username: A string, the username to use for this credential.
      password: A string, the password to use for this credential. If None,
        no password will be used.
      enable_password: A string, an optional enable password.
      ssh_private_key: A string, optional SSH private key data.
      ssh_private_key_file: The ssh_private_key as a stringIO file. Read-only.
    """

    def __init__(self, regexp=None, username=None, password=None,
                 enable_password=None, ssh_private_key=None, auto_enable=False,
                 connect_method=None, ssh_private_key_filename=None):
        """Initialiser.

        Args:
          regexp: A string, used to form the regexp class attribute.
        """
        if not isinstance(regexp, str):
            raise TypeError('regexp argument must be a str.')
        if not regexp.startswith('^'):
            regexp = '^' + regexp
        if not regexp.endswith('$'):
            regexp += '$'
        self._regexp_string = regexp
        self.regexp = re.compile(regexp, re.I)
        self.auto_enable = auto_enable
        self.connect_method = connect_method
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self._ssh_private_key = ssh_private_key
        self.ssh_private_key_filename = ssh_private_key_filename

    regexp_string = property(lambda self: self._regexp_string)

    def __eq__(self, other):
        return bool(
            self._regexp_string == other._regexp_string and
            self.username == other.username and
            self.password == other.password and
            self.enable_password == other.enable_password and
            self._ssh_private_key == other._ssh_private_key and
            self.ssh_private_key_filename == other.ssh_private_key_filename)

    def _ssh_private_key(self):
        return self._ssh_private_key

    def _set_ssh_private_key(self, key):
        self._ssh_private_key = key

    ssh_private_key = property(_ssh_private_key, _set_ssh_private_key)

    @property
    def ssh_private_key_file(self):
        return self._fileify_private_key()

    def _fileify_private_key(self):
        # TODO(afort): Deprecate the string based form for the filename form
        if self.ssh_private_key_filename is not None:
            return open(self.ssh_private_key_filename, 'r')
        elif self._ssh_private_key is not None:
            key_data = self._ssh_private_key
        else:
            key_data = ''
        return cStringIO.StringIO(key_data)

    def __repr__(self):
        return ('%s(regexp=%r, username=%r, bool(password)=%r, '
                'bool(enable_password)=%r, bool(ssh_private_key)=%r, '
                'ssh_private_key_filename=%r, '
                'auto_enable=%r, connect_method=%r)'
                % (self.__class__.__name__,
                   self.regexp_string,
                   self.username,
                   bool(self.password),
                   bool(self.enable_password),
                   bool(self.ssh_private_key),
                   self.ssh_private_key_filename,
                   bool(self.auto_enable),
                   self.connect_method))

    def matches(self, hostname):
        """Tests if this Credential matches the hostname.

        Args:
          hostname: A string, the hostname to check against the credential.

        Returns:
          A boolean. True iff the hostname matches for this credential.
          An empty hostname or None will not match.

        Raises:
          TypeError: if hostname is not a string (or None).
        """
        if not hostname:
            return False
        else:
            return bool(self.regexp.match(hostname) is not None)


class Credentials(object):
    """An abstract credentials information store.

    The credentials store holds a list of credentials, used for per-
    request credential match queries.

    Attributes:
      credentials: A list of Credential objects to match for hosts, in order.
    """

    def __init__(self, filename):
        self.credentials = []
        self.filename = filename
        try:
            self.credentials_file = open(filename)
        except (OSError, IOError), e:
            logging.error('Could not open credentials file. %s: %s',
                          e.__class__.__name__, str(e))
            self.credentials_file = None
        else:
            self.load_credentials()
            self.after_load_credentials()
            logging.debug('Loaded %d credentials.', len(self.credentials))

    def __len__(self):
        return len(self.credentials)

    def load_credentials(self):
        """Loads data from the credentials file."""
        raise NotImplementedError

    def after_load_credentials(self):
        """Handles anything required after loading the credentials."""
        # TODO(afort): Build a cache here for use by get_credential...

    def get_credential(self, hostname):
        """Gets a Credential object for the hostname supplied.

        Args:
          hostname: A string, the target hostname to get the credential for.

        Returns:
          A Credential instance.

        Raises:
          NoMatchingCredentialError: If there were no credentials for the host.
        """
        if not hostname:
            raise errors.NoMatchingCredentialError(
                'No credentials for host %r' % hostname)
        # TODO(afort): Use an O(1) algorithm.
        for credential in self.credentials:
            if credential.matches(hostname):
                return credential
        raise errors.NoMatchingCredentialError('No credentials for host %r' %
                                               hostname)


class YamlCredentials(Credentials):
    """Credentials loader that uses a YAML file with credentials in it."""

    def __init__(self, filename):
        super(YamlCredentials, self).__init__(filename)

    def load_credentials(self):
        credentials = []
        try:
            if self.credentials_file is not None:
                credentials = yaml.load(self.credentials_file)
                if isinstance(credentials, str):
                    credentials = []
                self.credentials_file.close()
        except yaml.error.YAMLError, e:
            logging.error('%s: %s', e.__class__.__name__, str(e))
            credentials = []

        if credentials:
            result = []
            for credential in credentials:
                # Empty YAML blocks (e.g., trailing '-') causes None elements.
                if credential is None:
                    continue
                # Defaults to matching all devices (if no regexp attrib).
                regexp = credential.get('regexp', '^.*$')
                auto_enable = credential.get('auto_enable')
                connect_method = credential.get('connect_method')
                username = credential.get('username')
                password = credential.get('password')
                enable_password = credential.get('enable_password')
                ssh_private_key = credential.get('ssh_private_key')
                ssh_private_key_filename = credential.get(
                    'ssh_private_key_filename')
                if username is None:
                    raise errors.MissingFieldError(
                        'username field in credential %r missing' % credential)
                result.append(
                    Credential(
                        regexp=regexp, username=username,
                        password=password,
                        enable_password=enable_password,
                        ssh_private_key=ssh_private_key,
                        auto_enable=auto_enable,
                        connect_method=connect_method,
                        ssh_private_key_filename=ssh_private_key_filename))
            self.credentials = result
        else:
            self.credentials = []


def guess_creds_file_format(filename):
    """Guesses the credentials file format based on extension."""
    for extension in CREDS_FILE_EXTENSIONS.iterkeys():
        if filename.endswith(extension):
            return CREDS_FILE_EXTENSIONS.get(extension)


def load_credentials_file(filename):
    """Loads a credentials file by name.

    Args:
      filename: A string, the config file name to load.

    Returns:
      An instance of a Credentials object subclass.

    Raises:
      UnknownCredentialsFileFormatError: The file format was not recognised.
    """
    format = guess_creds_file_format(filename)
    if format is not None:
        return format(filename)
    else:
        raise errors.UnknownCredentialsFileFormatError(
            'File %r not supported; supported extensions %r' %
            (filename, ', '.join(CREDS_FILE_EXTENSIONS.keys())))


# Map of file extensions to class used to import such a file.
CREDS_FILE_EXTENSIONS = {'.yaml': YamlCredentials}

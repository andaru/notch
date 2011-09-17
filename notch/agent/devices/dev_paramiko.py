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

"""Device model for 'unix-like' devices using Paramiko SSH2."""


import os
import socket
import tempfile

import paramiko

import notch.agent.errors

import device
import scp


class ParamikoDevice(device.Device):
    """Generic paramiko SSHv2 device model."""

    DEFAULT_CONNECT_METHOD = 'sshv2'
    DEFAULT_PORT = 22

    def __init__(self, name=None, addresses=None):
        super(ParamikoDevice, self).__init__(name=name, addresses=addresses)
        self.connect_methods = ('sshv2', )
        self._ssh_client = None
        self._port = None

    def _reconnect(self):
        self._connect(address=self.__address,
                      port=self.__port,
                      connect_method=self.__connect_method,
                      credential=self._current_credential)

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        self.__address = address
        self.__port = port
        self.__connect_method = connect_method
        self.__credential = credential
        # Just ignore the connect method, we only support sshv2.
        _ = connect_method

        self._port = port or self.DEFAULT_PORT
        if self._ssh_client is not None:
            self._ssh_client.close()
        # Load the private key, if available.
        if credential.ssh_private_key is not None:
            pkey = paramiko.RSAKey.from_private_key(
                credential.ssh_private_key_file)
        else:
            pkey = None
        self._ssh_client = paramiko.SSHClient()
        # TODO(afort): Be more secure.
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self._ssh_client.connect(str(address),
                                     port=self._port,
                                     username=credential.username,
                                     password=credential.password,
                                     pkey=pkey,
                                     timeout=self.timeouts.connect)
        except (paramiko.ssh_exception.SSHException, socket.error), e:
            raise notch.agent.errors.ConnectError(str(e))

    def _disconnect(self):
        self._ssh_client.close()
        self._ssh_client = None

    def __check_transport(self):
        transport = self._ssh_client.get_transport()
        if transport is None:
            self._reconnect()
            transport = self._ssh_client.get_transport()
        elif transport is not None and not transport.is_active():
            self._reconnect()
            transport = self._ssh_client.get_transport()
        return transport

    def _exec_command(self, command, bufsize=-1, combine_stderr=False,
                      timeout=None):
        transport = self.__check_transport()
        channel = transport.open_session()
        channel.set_combine_stderr(combine_stderr)
        timeout = timeout or self.timeouts.resp_long
        channel.settimeout(timeout)
        channel.exec_command(command)

        stdin = channel.makefile('wb', bufsize)
        stdout = channel.makefile('rb', bufsize)
        stderr = channel.makefile_stderr('rb', bufsize)
        return stdin, stdout, stderr

    def _command(self, command, mode=None):
        # mode argument is as yet unused. Quieten pylint.
        _ = mode
        try:
            stdin, stdout, stderr = self._exec_command(command,
                                                       combine_stderr=True)
        except (paramiko.ssh_exception.SSHException, EOFError), e:
            # TODO(afort): Catch any SSHExceptions we'd rather not retry on.
            exc = notch.agent.errors.CommandError(str(e))
            exc.retry = True
            raise exc
        else:
            stdin.close()
        try:
            return ''.join(stdout.readlines())
        finally:
            stdout.close()
            stderr.close()

    def download_file(self, source, destination, mode=None, overwrite=False):
        if not overwrite:
            if not os.path.exists(destination):
                raise notch.agent.errors.DownloadError('Destination path %r '
                                                       'does not exist'
                                                       % destination)
        transport = self.__check_transport()
        s = scp.ScpClient(transport)
        try:
            s.get(source, destination, preserve_times=True)
        except scp.ScpError, e:
            raise notch.agent.errors.DownloadError(str(e))

    def upload_file(self, source, destination, mode=None, overwrite=False):
        # TODO(afort): Handle overwrite (check remote filesystem?).
        transport = self.__check_transport()
        s = scp.ScpClient(transport)
        try:
            s.put(source, destination, preserve_times=True)
        except scp.ScpError, e:
            raise notch.agent.errors.DownloadError(str(e))

    def get_config(self, source, mode=None):
        tf = tempfile.NamedTemporaryFile()
        self.download_file(source, tf.name, mode=mode)
        tf.seek(0)
        return tf.read()

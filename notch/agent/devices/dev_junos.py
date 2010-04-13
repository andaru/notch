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

"""Juniper Networks JunOS device model."""


import logging
import socket

import paramiko

import notch.agent.errors

import device


class JunosDevice(device.Device):
    """Juniper Networks JunOS device model."""

    DEFAULT_CONNECT_METHOD = 'sshv2'
    DEFAULT_PORT = 22

    def __init__(self, name=None, addresses=None):
        super(JunosDevice, self).__init__(name=name, addresses=addresses)
        self.connect_methods = ('sshv2', )
        self._ssh_client = None
        self._port = None

    def _connect(self, address=None, port=None,
                 connect_method=None, credential=None):
        # Just ignore the connect method, we only support sshv2.
        _ = connect_method

        self._port = port or self.DEFAULT_PORT
        if self._ssh_client is not None:
            self._ssh_client.close()
        # Load the private key, if available.
        if credential.ssh_private_key is not None:
            pkey = paramiko.PKey.from_private_key(
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
        self._ssh_client == None

    def _exec_command(self, command, bufsize=-1, combine_stderr=False,
                      timeout=None):
        transport = self._ssh_client.get_transport()
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

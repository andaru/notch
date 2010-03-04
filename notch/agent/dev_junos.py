#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Juniper Networks JunOS device model."""


import logging
import socket

import paramiko

import device
import errors


class JunosDevice(device.Device):
    """Juniper Networks JunOS device model."""

    def __init__(self, name=None, addresses=None):
        super(JunosDevice, self).__init__(name=name, addresses=addresses)
        self._ssh_client = None

    def _connect(self, address=None, connect_method=None, credential=None):
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
                                     username=credential.username,
                                     password=credential.password,
                                     pkey=pkey)
        except (paramiko.ssh_exception.SSHException, socket.error), e:
            raise errors.ConnectError(str(e))

    def _exec_command(self, command, bufsize=-1, combine_stderr=False):
        transport = self._ssh_client.get_transport()
        channel = transport.open_session()

        channel.set_combine_stderr(combine_stderr)
        channel.exec_command(command)

        stdin = channel.makefile('wb', bufsize)
        stdout = channel.makefile('rb', bufsize)
        stderr = channel.makefile_stderr('rb', bufsize)
        return stdin, stdout, stderr
        
    def command(self, command, mode=None):
        # mode argument is as yet unused. Quieten pylint.
        _ = mode
        # TODO(afort): Combine output channels (e.g., for JunOS during
        # 'traceroute', where some output appears on stderr and some on stdout).
        try:
            stdin, stdout, stderr = self._exec_command(command,
                                                       combine_stderr=True)
        except paramiko.ssh_exception.SSHException, e:
            raise errors.CommandError(str(e))
        else:
            stdin.close()
        try:
            return ''.join(stdout.readlines())
        finally:
            stdout.close()
            stderr.close()

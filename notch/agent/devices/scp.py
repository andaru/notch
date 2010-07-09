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


import os
import socket


class Error(Exception):
    pass


class ScpError(Error):
    """An SCP error occured."""


class ScpClient(object):
    """A SCP client implementation."""

    def __init__(self, transport, tx_buffer_size=8192, rx_buffer_size=2048,
                 timeout=10.0, callback=None):
        self.transport = transport
        self.tx_buffer_size = tx_buffer_size
        self.rx_buffer_size = rx_buffer_size
        self.timeout = timeout
        self.callback = callback

        self.channel = None
        self._receive_path = None
        self._matime = None
        self._handle = None

    def put(self, file, remote_path='.', preserve_times=False):
        self.channel = self._channel()
        self.channel.exec_command('scp -t %s\n' % remote_path)
        self._response()
        self._send_file(file, preserve_times=True)

        if self.channel:
            self.channel.close()

    def _channel(self):
        channel = self.transport.open_session()
        channel.settimeout(self.timeout)
        return channel
        
    def get(self, remote_path, local_path='', preserve_times=False):
        self.channel = self._channel()
        self._receive_path = local_path or os.getcwd()
        preserve = ('', ' -p')[int(preserve_times)]
        self.channel.exec_command('scp%s -f %s' % (preserve, remote_path))
        self._command_response()

        if isinstance(local_path, file):
            self._handle = local_path
        else:
            self._handle = None
        
        if self.channel:
            self.channel.close()       

    def _response(self):
        msg = None
        try:
            msg = self.channel.recv(self.rx_buffer_size)
        except socket.timeout:
            raise ScpError('Timeout waiting for SCP response (%.2fs)' %
                           self.timeout)
        else:
            if msg and msg[0] == '\x00':
                # OK. Complete.
                return
            elif msg and msg[0] == '\x01':
                raise ScpError(msg[1:])
            elif self.channel.recv_stderr_ready():
                msg = self.channel.recv_stderr(self.rx_buffer_size)
                raise ScpError(msg)
            elif not msg:
                raise ScpError('No SCP repsonse from server.')
            
    def _command_response(self):
        command = {'C': self._recv_file,
                   'T': self._set_time,
                   }
        while not self.channel.closed:
            self.channel.sendall('\x00')
            msg = self.channel.recv(self.rx_buffer_size)
            if not msg:
                break
            try:
                command[msg[0]](msg[1:])
            except (KeyError, IndexError):
                raise ScpError(repr(msg))

    def _recv_file(self, command):
        parts = command.split()
        try:
            mode = int(parts[0], 8)
            size = int(parts[1])
            if os.path.isdir(self._receive_path):
                path = os.path.join(self._receive_path, parts[2])
            else:
                path = self._receive_path

        except (IndexError, AttributeError):
            self.channel.send('\x01')
            self.channel.close()
            raise ScpError('Invalid received file format. %r' % command)

        if not self._handle:
            try:
                handle = file(path, 'wb')
                self._handle = handle
            except IOError, e:
                self.channel.send('\x01')
                self.channel.close()
                raise
        else:
            handle = self._handle

        position = 0
        self.channel.send('\x00')
        bs = self.rx_buffer_size
        try:
            while position < size:
                if size - position <= bs:
                    bs = size - position
                handle.write(self.channel.recv(bs))
                position = handle.tell()
                if self.callback:
                    self.callback(position, size)
            msg = self.channel.recv(self.rx_buffer_size)
            if msg and msg[0] != '\x00':
                raise ScpError(msg[1:])
        except socket.timeout:
            self.channel.close()
            raise ScpError('Timed-out while receiving file.')

        handle.truncate()
        if not self._handle:
            try:
                os.utime(path, self._matime)
                self._matime = None
                os.chmod(path, mode)
            finally:
                # If a handle was not supplied by the user, close the one
                # we created.
                handle.close()
       
    def _stat(self, name):
        """Limited stat information required for SCP."""
        stats = os.stat(name)
        mode = oct(stats.st_mode)[-4:]
        return (mode, stats.st_size, int(stats.st_mtime), int(stats.st_atime))
                    
    def _send_file(self, fname, preserve_times=False):
        (mode, size, mtime, atime) = self._stat(name)
        if preserve_times:
            self._update_time(mtime, atime)
        handle = file(fname, 'rb')
        filename = os.path.basename(fname)
        self.channel.sendall('C%s %d %s\n' % (mode, size, filename))
        self._response()

        position = 0
        while position < size:
            self.channel.sendall(handle.read(self.tx_buffer_size))
            position = handle.tell()
            if self.callback:
                self.callback(position, size)
        self.channel.sendall('\x00')
        handle.close()

    def _update_time(self, mtime, atime):
        self.channel.sendall('T%d 0 %d 0\n' % (mtime, atime))

    def _set_time(self, command):
        try:
            parts = command.split()
            mtime = int(parts[0])
            atime = int(parts[2]) or mtime
        except (AttributeError, IndexError):
            self.channel.send('\x01')
            raise ScpError('Invalid time format: %r' % command)
        else:
            self._matime = (mtime, atime)
        

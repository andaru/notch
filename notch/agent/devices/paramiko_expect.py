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

import select

import pexpect


class ParamikoSpawn(pexpect.spawn):
    """A pexpect.spawn that works with Paramiko Channel objects.

    The Channel object returned by paramiko.SSHClient.invoke_shell()
    is suitable for use with this class.

    Attributes:
      child_fd: A paramiko.Channel object, the SSH channel (like a socket).
    """

    def _set_channel(self, channel):
        self.child_fd = channel

    channel = property(lambda x: x.child_fd, _set_channel)

    @property
    def transport(self):
        return self.child_fd.get_transport()

    def isalive(self):
        try:
            return self.child_fd.get_transport().is_active()
        except AttributeError:
            return False

    def read_nonblocking(self, size=-1, timeout=-1):
        if self.child_fd == -1:
            raise ValueError('I/O operation on closed file')

        if not self.isalive():
            r, w, e = select.select([self.child_fd], [], [], 0)
            if not r:
                self.flag_eof = True
                raise pexpect.EOF('End Of File (EOF) in read(). '
                                  'Braindead platform.')

        if timeout == -1:
            timeout = self.timeout

        r, w, e = select.select([self.child_fd], [], [], timeout)
        if not r:
            raise pexpect.TIMEOUT('Timeout (%s) exceeded in read().' %
                                  str(timeout))

        if self.child_fd in r:
            try:
                s = self.child_fd.recv(size)
            except OSError, e:
                self.flag_eof = True
                raise pexpect.EOF('End Of File (EOF) in read(). '
                                  'Exception style platform.')
            if s == '':
                self.flag_eof = True
                raise pexpect.EOF('End Of File (EOF) in read(). '
                                  'Empty string style platform.')

            if self.logfile is not None:
                self.logfile.write(s)
                self.logfile.flush()

            return s

        raise pexpect.ExceptionPexpect('Reached an unexpected state in read().')

    def send(self, s):
        return self.child_fd.send(s)

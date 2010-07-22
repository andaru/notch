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

"""Tests for the lb_transport module."""


import mox
import os
import unittest
import xmlrpclib

from notch.client import lb_transport


class BackendTest(mox.MoxTestBase):
    
    def testBackend(self):
        trans = self.mox.CreateMock(xmlrpclib.Transport)
        self.mox.ReplayAll()
        be = lb_transport.Backend(address='127.0.0.1')
        be.transport = trans
        self.assertEqual('127.0.0.1', be.address)
        be.address = '127.0.0.2'
        self.assertEqual('127.0.0.2', be.address)
        self.assertEqual(trans, be.transport)
        self.mox.VerifyAll()

        
class BackendPolicyTest(mox.MoxTestBase):
    
    def testBackendPolicy(self):
        trans = self.mox.CreateMock(xmlrpclib.Transport)
        self.mox.ReplayAll()
        be1 = lb_transport.Backend(address='127.0.0.1')
        be1.transport = trans
        be2 = lb_transport.Backend(address='127.0.0.2')
        be2.transport = trans

        pol = lb_transport.BackendPolicy([be1, be2])
        self.assertEqual(len(pol.backends), 2)
        self.mox.VerifyAll()

    def testRoundRobinPolicy(self):
        trans = self.mox.CreateMock(xmlrpclib.Transport)
        self.mox.ReplayAll()
        be1 = lb_transport.Backend(address='127.0.0.1')
        be1.transport = trans
        be2 = lb_transport.Backend(address='127.0.0.2')
        be2.transport = trans

        pol = lb_transport.RoundRobinPolicy([be1, be2])
        iterator = iter(pol)
        first = iterator.next()
        second = iterator.next()
        third = iterator.next()
        self.assert_(first == be1 or first == be2)
        self.assert_(first != second)
        self.assert_(third == first)
        self.mox.VerifyAll()

    def testRandomPolicy(self):
        trans = self.mox.CreateMock(xmlrpclib.Transport)
        self.mox.ReplayAll()
        be1 = lb_transport.Backend(address='127.0.0.1')
        be1.transport = trans
        be2 = lb_transport.Backend(address='127.0.0.2')
        be2.transport = trans
        be3 = lb_transport.Backend(address='127.0.0.3')
        be3.transport = trans

        pol = lb_transport.RoundRobinPolicy([be1, be2, be3])
        iterator = iter(pol)
        be_seen = set()
        for _ in xrange(10):
            # Our chances of getting both backends are remarkably high.
            # But this is an imperfect test, for sure.
            be_seen.add(iterator.next())
        self.assert_(be1 in be_seen)
        self.assert_(be2 in be_seen)
        self.assert_(be3 in be_seen)
        self.mox.VerifyAll()


if __name__ == '__main__':
    unittest.main()

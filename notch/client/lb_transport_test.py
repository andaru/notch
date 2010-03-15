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
import unittest
import os

import lb_transport

import xmlrpclib


class LoadBalancingTransportTest(unittest.TestCase):

    def testHostForm(self):
        t = lb_transport.LoadBalancingTransport()
        self.assertEqual(t.host_form('localhost:8080'), 'localhost')
        self.assertEqual(t.host_form('localhost: 8080'), 'localhost')
        self.assertEqual(t.host_form('localhost : 8080'), 'localhost')
        self.assertEqual(t.host_form('localhost'), 'localhost')
        self.assertEqual(t.host_form('localhost '), 'localhost')
        self.assertEqual(t.host_form(' localhost'), 'localhost')
        self.assertEqual(t.host_form(' localhost '), 'localhost')


if __name__ == '__main__':
    unittest.main()

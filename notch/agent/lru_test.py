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

"""Tests for the lru module."""


import eventlet

from eventlet.green import time
import unittest

import lru


class LruTest(unittest.TestCase):

    def testLruBasic(self):
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_size=2)
        test_lru[5]
        self.assertEqual(test_lru[5], 10)
        self.assertEqual(test_lru[10], 20)
        self.assertEqual(test_lru[20], 40)
        self.assertEqual(len(test_lru), 2)

    def testLruExpiry(self):
        called = []
        def callback(input):
            return input*3

        def expire(key, value):
            called.append(True)

        test_lru = lru.LruDict(callback, expire_callback=expire,
                               maximum_size=2)
        self.assertEqual(test_lru[5], 15)
        self.assertEqual(test_lru[10], 30)
        self.assert_(not called)
        self.assertEqual(test_lru['10'], '101010')
        self.assert_(called)
        self.assertEqual(len(test_lru), 2)

    def testExpireItem(self):
        def callback(input):
            return input*3

        test_lru = lru.LruDict(callback, maximum_size=2)
        test_lru[5]
        test_lru[10]
        self.assertEqual(test_lru.expire_item(), 15)
        self.assertEqual(test_lru.expire_item(), 30)
        self.assertRaises(IndexError, test_lru.expire_item)

    def testSetItem(self):
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_size=2)
        # Override the callback function by direct setting.
        test_lru[10] = 40
        self.assertEqual(test_lru[10], 40)
        self.assertEqual(test_lru[20], 40)

    def testLruSameItem(self):
        """Item keys are only added to the cache once."""
        def callback(input):
            return input

        test_lru = lru.LruDict(callback, maximum_size=2)
        self.assertEqual(test_lru[10], 10)
        self.assertEqual(len(test_lru), 1)
        self.assertEqual(test_lru[10], 10)
        self.assertEqual(len(test_lru), 1)

    def testLruSameItemWithExpiry(self):
        """Item keys are re-added to the cache upon expiry."""
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_size=2)
        self.assertEqual(test_lru[10], 20)
        self.assertEqual(len(test_lru), 1)
        self.assertEqual(test_lru[10], 20)
        self.assertEqual(len(test_lru), 1)
        self.assertEqual(test_lru[20], 40)
        self.assertEqual(len(test_lru), 2)
        self.assertEqual(test_lru[10], 20)
        self.assertEqual(len(test_lru), 2)
        self.assertEqual(test_lru[20], 40)
        self.assertEqual(len(test_lru), 2)
        self.assertEqual(test_lru[20], 40)
        self.assertEqual(len(test_lru), 2)

    def testLruChangePopulateCallback(self):
        def callback1(input):
            return input

        def callback2(input):
            return input*2

        my_lru = lru.LruDict(callback1, maximum_size=1)
        self.assertEqual(my_lru[10], 10)
        self.assertEqual(len(my_lru), 1)
        self.assertEqual(my_lru[10], 10)
        self.assertEqual(len(my_lru), 1)

        my_lru.set_populate_callback(callback2)
        self.assertEqual(my_lru[10], 20)
        self.assertEqual(len(my_lru), 1)

    def testLruChangeExpireCallback(self):
        called = []

        def callback(input):
            return input*3

        def expire(key, value):
            called[:] = []

        def expire_new(key, value):
            called.append(True)

        test_lru = lru.LruDict(callback, expire_callback=expire, maximum_size=2)
        self.assert_(not called)
        self.assertEqual(test_lru[5], 15)
        self.assertEqual(test_lru[10], 30)
        self.assert_(not called)
        self.assertEqual(len(test_lru), 2)
        test_lru.set_expire_callback(expire_new)
        self.assert_(not called)
        self.assertEqual(test_lru['10'], '101010')
        self.assert_(called)
        self.assertEqual(len(test_lru), 2)

    def testExpireItemForLruHeapOrder(self):
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_size=4)
        test_lru[10]
        test_lru[20]
        test_lru[30]
        test_lru['40']
        self.assertEqual(20, test_lru.expire_item())
        self.assertEqual(40, test_lru.expire_item())
        self.assertEqual(60, test_lru.expire_item())
        self.assertEqual('4040', test_lru.expire_item())

    def testExpireItemForLruHeapOrderDuringExpiry(self):
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_size=4)
        test_lru[100]  # will be expired.
        test_lru[200]  # will be expired.
        test_lru[300]  # will be expired.
        test_lru['400']  # will be expired.
        test_lru[10]
        test_lru[20]
        test_lru[30]
        test_lru['40']
        self.assertEqual(20, test_lru.expire_item())
        self.assertEqual(40, test_lru.expire_item())
        self.assertEqual(60, test_lru.expire_item())
        self.assertEqual('4040', test_lru.expire_item())
        test_lru[10]  # will be expired.
        test_lru[20]
        test_lru[30]
        test_lru['40']
        test_lru['50']
        self.assertEqual(40, test_lru.expire_item())
        self.assertEqual(60, test_lru.expire_item())
        self.assertEqual('4040', test_lru.expire_item())
        self.assertEqual('5050', test_lru.expire_item())

    def testExpireItemReturnCopy(self):
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_size=4)
        test_lru[100]
        item = test_lru.expire_item(return_copy=True)
        self.assertEqual(item, 200)
        self.assert_(100 not in test_lru)

        test_lru[200]
        item = test_lru.expire_item() # return_copy=True is the default.
        self.assertEqual(item, 400)
        self.assert_(200 not in test_lru)

    def testExpireItemDontReturnCopy(self):
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_size=4)
        test_lru[100]
        item = test_lru.expire_item(return_copy=False)
        self.assertEqual(item, None)
        self.assert_(100 not in test_lru)
        
    def testLruGet(self):
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_size=4)
        test_lru[100]
        self.assertEqual(test_lru.get(100), 200)
        self.assertEqual(test_lru.get('not here'), None)
        self.assertEqual(test_lru.get('not there', default='foo'), 'foo')

    def testLruAgeExpiry(self):
        def callback(input):
            return input*2

        test_lru = lru.LruDict(callback, maximum_age=0.1)
        test_lru[100]
        self.assert_(100 in test_lru)
        time.sleep(0.2)
        self.assert_(100 not in test_lru)

    def testLruDontExpireSignal(self):
        def callback(input):
            return input*3

        def expire(key, value):
            # We won't cause this item to be expired.
            raise lru.DontExpireError

        test_lru = lru.LruDict(callback, expire_callback=expire,
                               maximum_size=2)
        self.assertEqual(test_lru[5], 15)
        self.assertEqual(test_lru[10], 30)
        self.assertEqual(test_lru['10'], '101010')
        self.assertEqual(len(test_lru), 3)


if __name__ == '__main__':
    unittest.main()

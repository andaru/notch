#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Tests for the lru module."""


import unittest

import lru


class LruTest(unittest.TestCase):

    def testLruBasic(self):
        def callback(input):
            return input*2

        self.lru = lru.LruDict(callback, maximum_size=2)
        self.lru[5]
        self.assertEqual(self.lru[5], 10)
        self.assertEqual(self.lru[10], 20)
        self.assertEqual(self.lru[20], 40)
        self.assertEqual(len(self.lru), 2)

    def testLruExpiry(self):
        called = []
        def callback(input):
            return input*3

        def expire(key, value):
            called.append(True)

        self.lru = lru.LruDict(callback, expire_callback=expire,
                               maximum_size=2)
        self.assertEqual(self.lru[5], 15)
        self.assertEqual(self.lru[10], 30)
        self.assert_(not called)
        self.assertEqual(self.lru['10'], '101010')
        self.assert_(called)
        self.assertEqual(len(self.lru), 2)

    def testExpireItem(self):
        def callback(input):
            return input*3

        self.lru = lru.LruDict(callback, maximum_size=2)
        self.lru[5]
        self.lru[10]
        self.assertEqual(self.lru.expire_item(), 15)
        self.assertEqual(self.lru.expire_item(), 30)
        self.assertRaises(IndexError, self.lru.expire_item)

    def testSetItem(self):
        def callback(input):
            return input*2

        self.lru = lru.LruDict(callback, maximum_size=2)
        # Override the callback function by direct setting.
        self.lru[10] = 40
        self.assertEqual(self.lru[10], 40)
        self.assertEqual(self.lru[20], 40)

    def testLruSameItem(self):
        """Item keys are only added to the cache once."""
        def callback(input):
            return input

        self.lru = lru.LruDict(callback, maximum_size=2)
        self.assertEqual(self.lru[10], 10)
        self.assertEqual(len(self.lru), 1)
        self.assertEqual(self.lru[10], 10)
        self.assertEqual(len(self.lru), 1)

    def testLruSameItemWithExpiry(self):
        """Item keys are re-added to the cache upon expiry."""
        def callback(input):
            return input*2

        self.lru = lru.LruDict(callback, maximum_size=2)
        self.assertEqual(self.lru[10], 20)
        self.assertEqual(len(self.lru), 1)
        self.assertEqual(self.lru[10], 20)
        self.assertEqual(len(self.lru), 1)
        self.assertEqual(self.lru[20], 40)
        self.assertEqual(len(self.lru), 2)
        self.assertEqual(self.lru[10], 20)
        self.assertEqual(len(self.lru), 2)
        self.assertEqual(self.lru[20], 40)
        self.assertEqual(len(self.lru), 2)
        self.assertEqual(self.lru[20], 40)
        self.assertEqual(len(self.lru), 2)

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

        self.lru = lru.LruDict(callback, expire_callback=expire, maximum_size=2)
        self.assert_(not called)
        self.assertEqual(self.lru[5], 15)
        self.assertEqual(self.lru[10], 30)
        self.assert_(not called)
        self.assertEqual(len(self.lru), 2)
        self.lru.set_expire_callback(expire_new)
        self.assert_(not called)
        self.assertEqual(self.lru['10'], '101010')
        self.assert_(called)
        self.assertEqual(len(self.lru), 2)

    def testExpireItemForLruHeapOrder(self):
        def callback(input):
            return input*2

        self.lru = lru.LruDict(callback, maximum_size=4)
        self.lru[10]
        self.lru[20]
        self.lru[30]
        self.lru['40']
        self.assertEqual(20, self.lru.expire_item())
        self.assertEqual(40, self.lru.expire_item())
        self.assertEqual(60, self.lru.expire_item())
        self.assertEqual('4040', self.lru.expire_item())

    def testExpireItemForLruHeapOrderDuringExpiry(self):
        def callback(input):
            return input*2

        self.lru = lru.LruDict(callback, maximum_size=4)
        self.lru[100]  # will be expired.
        self.lru[200]  # will be expired.
        self.lru[300]  # will be expired.
        self.lru['400']  # will be expired.
        self.lru[10]
        self.lru[20]
        self.lru[30]
        self.lru['40']
        self.assertEqual(20, self.lru.expire_item())
        self.assertEqual(40, self.lru.expire_item())
        self.assertEqual(60, self.lru.expire_item())
        self.assertEqual('4040', self.lru.expire_item())
        self.lru[10]  # will be expired.
        self.lru[20]
        self.lru[30]
        self.lru['40']
        self.lru['50']
        self.assertEqual(40, self.lru.expire_item())
        self.assertEqual(60, self.lru.expire_item())
        self.assertEqual('4040', self.lru.expire_item())
        self.assertEqual('5050', self.lru.expire_item())


if __name__ == '__main__':
    unittest.main()

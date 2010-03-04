#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""A callback-populated least-recently used cache that behaves like a dict."""

import copy
import heapq
import time
import UserDict

# pylint:disable-msg=R0903
class HeapItem(object):
    """A cached key kept on the heap queue from the data dictionary."""
    def __init__(self, key):
        self.time = time.time()
        self.key = key

    def __lt__(self, other):
        if self.time < other.time:
            return True
        else:
            return False


class LruDict(UserDict.IterableUserDict):
    """A least-recently used cache style dictionary.

    Attributes:
      populate_callback: A callable, the method to call (with the item key)
        to populate the dictionary value for that key.
      expire_callback: Optional callable, the method to call (with key
        and value arguments) when
    """

    def __init__(self, populate_callback=None, expire_callback=None,
                 maximum_size=1024):
        self._expire_callback = expire_callback
        self.maximum_size = maximum_size
        self._populate_callback = populate_callback
        self._heap = []
        self.data = {}
        self._initialise()

    def _initialise(self):
        self._heap[:] = []
        self.data.clear()
        self._dirty = False

    def expire_item(self, return_copy=True):
        """Expires an item and optionally returns a shallow copy of it.

        Args:
          return_copy: A boolean, if True, returns a copy of the expired item.

        Raises:
          IndexError: if the LRU is empty.
        """
        item = heapq.heappop(self._heap)
        value = self.data.get(item.key)
        if return_copy:
            result = copy.copy(value)
        else:
            result = None
        del self.data[item.key]
        return result

    def get(self, key, default=None):
        """Returns the named key's value from the cache."""
        if key in self.data:
            return self.data[key]
        else:
            return default

    def set_populate_callback(self, callback):
        """Sets the population callback for the populate_callback attribute."""
        self._initialise()
        self._populate_callback = callback

    def set_expire_callback(self, callback):
        """Sets the expiry callback for the expire_callback attribute."""
        self._expire_callback = callback

    def __getitem__(self, key):
        """Gets the value for key from the cache."""
        if key not in self.data or self._dirty:
            value = self._populate_callback(key)
            self._push_and_set(key, value)
            if self._dirty:
                self._dirty = False
        return self.data[key]

    def __setitem__(self, key, value):
        """Sets the value for key to the cache."""
        self._push_and_set(key, value)

    def _push_and_set(self, key, value):
        """Pushes an item onto the heap and sets it in the cache."""
        item = HeapItem(key)
        if len(self._heap) < self.maximum_size:
            heapq.heappush(self._heap, item)
        else:
            old_item = heapq.heapreplace(self._heap, item)
            self._expire_item(old_item.key)
        self.data[key] = value

    def _expire_item(self, key):
        """Expires an item from the cache."""
        if self._expire_callback and key in self.data:
            self._expire_callback(key, self.data[key])
        if key in self.data:
            del self.data[key]

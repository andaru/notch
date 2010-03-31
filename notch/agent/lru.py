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

"""A callback-populated least-recently used cache that behaves like a dict."""

import copy
import heapq
import time
import UserDict

import eventlet


class Error(Exception):
    pass


class DontPopulateItemError(Error):
    """Indicate to the LRU that this item should not be cached."""


class DontExpireError(Error):
    """Indicate to the LRU that this key should not be expired."""


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

    This dictionary is not thread-safe, though it should not explode.
    Particularly, boundaries (such as maximum_size) may not be respected.

    Attributes:
      populate_callback: A callable, the method to call (with the item key)
        to populate the dictionary value for that key.
      expire_callback: Optional callable, the method to call (with key
        and value arguments) when
      maximum_size: An int, the maximum cache size. Not reliable in a multi-
        threaded environment (the respected maximum size may be up to
        num_threads higher).
      maximum_age: A float, the cache entry lifetime. Setting this to 0 or None
        disables automatic aging for all new items entering the cache.
    """

    def __init__(self, populate_callback=None, expire_callback=None,
                 maximum_size=1024, maximum_age=None, dict=None):
        UserDict.IterableUserDict.__init__(self, dict=dict)
        self._expire_callback = expire_callback
        self.maximum_size = maximum_size
        self.maximum_age = maximum_age
        self._populate_callback = populate_callback
        self._heap = []
        self.data = {}
        self._cleanup_gts = set()
        self._initialise()

    def _initialise(self):
        self._heap[:] = []
        self.data.clear()
            
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
        self._expire_item(item.key)
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
        """Gets the value for key from the cache, maybe populating it first."""
        if key not in self.data:
            try:
                value = self._populate_callback(key)
            except DontPopulateItemError:
                return None
            except Exception, e:
                raise e
            self._push_and_set(key, value)
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
        if self.maximum_age:
            self._cleanup_gts.add(
                eventlet.spawn_after(self.maximum_age, self._expire_item, key))

    def _expire_item(self, key):
        """Expires an item from the cache."""
        if self._expire_callback and key in self.data:
            try:
                self._expire_callback(key, self.data[key])
            except DontExpireError:
                # If this exception is raised, we won't expire the item.
                return
            except Exception, e:
                raise e
        try:
            del self.data[key]
        except KeyError:
            # Indicates a race condition, multi-threaded use.
            pass

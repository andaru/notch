#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""An executor pool.

A very simple execute only thread pool for background execution of
Notch RPC handlers.
"""


import logging
import Queue
import threading
import time
import traceback

# Default number of threads to have in the pool. Thread count, and
# specifically contention, is the major factor in jitter due to
# queueing artifacts. More threads are necessary when an agent must
# talk to many devices simultaneously, to allow for the combined
# effects of network latency. Sharding work amongst multiple agents
# using a reverse proxy load-balancer is a useful scaling strategy.
DEFAULT_NUM_THREADS = 8

# Time to sleep when the queue is full on put() and block=True.
DEFAULT_QUEUE_FULL_SLEEP_TIME = 1.0


class ThreadPool(object):
    """A simple thread pool of executor threads.

    Threads execute work items from a queue (a callable, args and kwargs).
    Work items are executed, their results are ignored.  Exceptions details
    are logged, but otherwise ignored.

    Attributes:
      num_threads: An integer, the number of threads to use in the pool.
      daemon_threads: A bool, iff True, threads are daemonised.
      max_q_in_depth: An integer, the maximum queue depth.
    """

    def __init__(self, num_threads=DEFAULT_NUM_THREADS, daemon_threads=True,
                 max_q_in_depth=None):
        self.num_threads = num_threads
        self.max_q_in_depth = max_q_in_depth
        if self.max_q_in_depth:
            self._q_in = Queue.Queue(self.max_q_in_depth)
        else:
            self._q_in = Queue.Queue()
        self._stopped = False
        self._threads = {}
        for i in xrange(self.num_threads):
            name = 'thread-%d' % i
            self._threads[name] = threading.Thread(target=self._process_q,
                                                   name=name)
            self._threads[name].start()

    def put(self, task, *args, **kwargs):
        """Places a work item on the queue.

        Args:
          task: A callable to execute.
          args: Non-keyword arguments.
          kwargs: Keyword arguments, including 'block' (bool). If block is
            True, block until the item is queued.  If False, exceptions raised.

        Raises:
          Queue.Full: If the ThreadPool has a max_q_in_depth, this may occur
          when not running in blocking mode.
        """
        while True:
            try:
                return self._q_in.put_nowait((task, args, kwargs))
            except Queue.Full:
                if 'block' in kwargs and kwargs['block']:
                    time.sleep(sleep_time)
                else:
                    raise

    def stop(self):
        """Stops the ThreadPool."""
        self._stopped = True
        for thread in self._threads.itervalues():
            thread.join()

    def _process_q(self):
        """Processes queue items; executed by worker threads."""
        while not self._stopped:
            try:
                task, a, kwa = self._q_in.get(True, 1.0)
            except Queue.Empty:
                continue
            try:
                # Execute the work item.
                task(*a, **kwa)
            except Exception, e:
                logging.error('Unhandled exception occured in %s. %s: %s\n%s',
                              self.__class__.__name__,
                              str(e.__class__), str(e),
                              traceback.format_exc())

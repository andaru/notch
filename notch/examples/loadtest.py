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

"""A simple loadtest using the Notch Client."""

import sys
from eventlet.green import time
import notch.client

COUNT = 50000

def c(r):
    pass
    
def main(argv):
    if len(argv):
        try:
            count = int(argv[1])
        except ValueError:
            count = COUNT
    else:
        count = COUNT

    nc = notch.client.Connection(['localhost:8080', 'localhost:8081',
                                 'localhost:8082', 'localhost:8083'])
    
    r = notch.client.Request('command', {'command': 'banner foo',
                                         'device_name': 'localhost'},
                             callback=c)
           
    for _ in xrange(count):
        nc.exec_request(r)
    nc.wait_all()
    


if __name__ == '__main__':
    sys.exit(main(sys.argv))

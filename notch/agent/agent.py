#!/usr/bin/env python
"""Agent binary wrapper script.

Runs the code in __main__ module like python -m in 2.7/3.1+ does.
"""

import os
import runpy


PKG = 'notch.agent'

def main():
    try:
        run_globals = runpy.run_module(PKG, run_name='__main__', alter_sys=True)
        executed = os.path.splitext(
            os.path.basename(run_globals['__file__']))[0]
        if executed != '__main__':  # For Python 2.5 compatibility
            raise ImportError('Incorrectly executed %s instead of __main__' %
                              executed)
    except ImportError:  # For Python 2.6 compatibility
        runpy.run_module(
            '%s.__main__' % PKG, run_name='__main__', alter_sys=True)

if __name__ == '__main__':
    main()

## {{{ http://code.activestate.com/recipes/577088/ (r1)
#!/usr/bin/env python
import os
import runpy

"""Agent binary wrapper script.

Runs the code in __main__ module like python -m in 2.7/3.1+ does.
"""

PKG = 'notch.agent'

try:
    run_globals = runpy.run_module(PKG, run_name='__main__', alter_sys=True)
    executed = os.path.splitext(os.path.basename(run_globals['__file__']))[0]
    if executed != '__main__':  # For Python 2.5 compatibility
        raise ImportError('Incorrectly executed %s instead of __main__' %
                            executed)
except ImportError:  # For Python 2.6 compatibility
    runpy.run_module('%s.__main__' % PKG, run_name='__main__', alter_sys=True)
## end of http://code.activestate.com/recipes/577088/ }}}


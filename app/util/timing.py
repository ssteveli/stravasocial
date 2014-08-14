__author__ = 'ssteveli'

import functools
import time

def timing(name=None):
    def timed(f):
        def wrapper(*args, **kw):
            ts = time.time()
            result = f(*args, **kw)
            te = time.time()

            print '%r (%r, %r, %r) %2.4f sec' % \
                  (f.__name__ if name is None else name, f.__name__, args, kw, te-ts)
            return result

        return functools.wraps(f)(wrapper)

    return timed

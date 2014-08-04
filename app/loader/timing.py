__author__ = 'ssteveli'

import time
import functools

def timing(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        time1 = time.time()
        ret = f(*args, **kwargs)
        time2 = time.time()

        print 'timer: (%s) function took (%0.3f)ms' % (f.func_name, (time2-time1)*1000.0)
        return ret
    return wrap
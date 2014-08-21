__author__ = 'ssteveli'

import json

def _default(self, o):
    if isinstance(o, set):
        return list(o)

    return o.__dict__

json.JSONEncoder.default = _default

class Athlete(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
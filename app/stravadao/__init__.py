import pyconfig

from stravalib.model import Activity, BaseEffort, Athlete
from stravalib import Client
from util.timing import timing

__author__ = 'ssteveli'

def activity_get_state(self):
    activity = {
        'id': self.id,
        'name': self.name,
        'segment_efforts': []
    }

    for effort in list(self.segment_efforts):
        activity['segment_efforts'].append({
            'segment': {
                'id': effort.segment.id,
                'name': effort.segment.name,
                'average_grade': effort.segment.average_grade
            },
            'athlete': {
                'id': self.athlete.id if self.athlete is not None and self.athlete.id is not None else -1
            },
            'activity': {
                'id': self.id
            },
            'moving_time': effort.moving_time.total_seconds(),
            'elapsed_time': effort.elapsed_time.total_seconds(),
            'distance': effort.distance.get_num(),
            'average_watts': effort.average_watts,
            'average_heartrate': effort.average_heartrate,
            'max_heartrate': effort.max_heartrate,
            'average_cadence': effort.average_cadence
        })
    return activity

def activity_set_state(self, d):
    self.__init__(d)
    self.from_dict(d)

def effort_get_state(self):
    effort = {
            'id': self.id,
            'name': self.name,
            'segment': {
                'id': self.segment.id,
                'name': self.segment.name,
                'average_grade': self.segment.average_grade
            },
            'athlete': {
                'id': self.athlete.id
            },
            'activity': {
                'id': self.id
            },
            'moving_time': self.moving_time.total_seconds(),
            'elapsed_time': self.elapsed_time.total_seconds(),
            'distance': self.distance.get_num(),
            'average_watts': self.average_watts,
            'average_heartrate': self.average_heartrate,
            'max_heartrate': self.max_heartrate,
            'average_cadence': self.average_cadence
    }
    return effort

def effort_set_state(self, d):
    self.__init__(d)
    self.from_dict(d)

def athlete_get_state(self):
    athlete = {
        'id': self.id,
        'firstname': self.firstname,
        'lastname': self.lastname,
        'profile': self.profile,
        'measurement_preference': self.measurement_preference
    }
    return athlete

def athlete_set_state(self, d):
    self.__init__(d)
    self.from_dict(d)

Activity.__getstate__ = activity_get_state
Activity.__setstate__ = activity_set_state
BaseEffort.__getstate__ = effort_get_state
BaseEffort.__setstate__ = effort_set_state
Athlete.__getstate__ = athlete_get_state
Athlete.__setstate__ = athlete_set_state




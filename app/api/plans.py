__author__ = 'ssteveli'

from pymongo import MongoClient
from pymongo import DESCENDING
import datetime
import calendar
from features import FeatureFlags
import pyconfig

class Plan():

    def __init__(self, athlete):
        self.athlete = athlete
        self.ff = FeatureFlags()
        self.reload()

    @pyconfig.reload_hook
    def reload(self):
        self.mongo = MongoClient(pyconfig.get('mongodb.host', 'strava-mongodb'), int(pyconfig.get('mongodb.port', '27017')))
        self.db = self.mongo.stravasocial
        self.plans = self.db.plans
        self.comparisons = self.db.comparisons

    def get_plan(self):
        athlete_plan = 'default'
        if 'plan' in self.athlete:
            athlete_plan = self.athlete['plan']

        dbplan = self.plans.find_one({'_id': athlete_plan})
        if dbplan is None:
            dbplan = {
                "_id": "default",
                "delay": 60 * 15 # default is 15 minutes
            }

        if not self.ff.isOn('comparisons', default=True):
            dbplan['is_execution_allowed'] = False
            dbplan['next_execution_msg'] = 'comparisons are currently turned off'
            dbplan['next_execution_code'] = 'DISABLED'
            return dbplan

        is_execution_allowed = False
        # unlimited plans will have a delay of -1
        if dbplan['delay'] == -1:
            is_execution_allowed= True
        else:
            # get the last comparison this athlete ran
            cur = self.comparisons.find({"athlete_id": self.athlete['athlete_id']}).sort("started_ts", DESCENDING).limit(1)

            if cur is None or cur.count() == 0:
                is_execution_allowed = True
            else:
                c = cur.next()
                dbplan['last_execution_time'] = self.time_to_millies(datetime.datetime.fromtimestamp(c['started_ts']))/1000

                if c['state'] == "Running":
                    is_execution_allowed = False
                    dbplan['next_execution_msg'] = 'must wait until the current comparison is completed'
                    dbplan['next_execution_code'] = 'JOB_RUNNING'
                else:
                    diff = datetime.datetime.now() - datetime.datetime.fromtimestamp(c['started_ts'])

                    if diff.seconds < dbplan['delay']:
                        is_execution_allowed = False

                        dbplan['next_execution_time'] = self.time_to_millies(datetime.datetime.fromtimestamp(c['started_ts']) + datetime.timedelta(0, dbplan['delay']))/1000
                        dbplan['next_execution_msg'] = 'must wait until the specified time'
                        dbplan['next_execution_code'] = 'ENFORCED_DELAY'
                    else:
                        is_execution_allowed = True

        dbplan['is_execution_allowed'] = is_execution_allowed

        return dbplan


    def time_to_millies(self, dt):
        if dt.utcoffset() is not None:
                dt = dt - dt.utcoffset()
        millis = int(calendar.timegm(dt.timetuple()) * 1000 +
            dt.microsecond / 1000)
        return millis


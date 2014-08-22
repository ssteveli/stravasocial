__author__ = 'ssteveli'

import gearman
from StravaCompare import StravaCompare
from bson import json_util, ObjectId
import json
import traceback
from pymongo import MongoClient
import time
import pyconfig

import logging
import logging.handlers

log = logging.getLogger("stravacompare")
log.setLevel(logging.DEBUG)

file = logging.handlers.RotatingFileHandler('/data/log/stravacompare-worker.log', backupCount=5)
file.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file.setFormatter(formatter)
log.addHandler(file)

class Container():
    def __init__(self):
        self.reload()

    @pyconfig.reload_hook
    def reload(self):
        self.client = MongoClient(pyconfig.get('mongodb.host', 'strava-mongodb'), int(pyconfig.get('mongodb.port', '27017')))
        self.db = self.client.stravasocial
        self.comparisons = self.db.comparisons
        self.gmworker = gearman.GearmanWorker(['strava-gearmand:4730'])

c = Container()

def handle_event(event_type, **kwargs):
    if event_type == 'started':
        c.comparisons.update({'_id': kwargs['id']}, {'$set': {
            'state': 'Running',
            'started_ts': kwargs['started_ts']
        }}, upsert=True)
    elif event_type == 'activity':
        c.comparisons.update({'_id': kwargs['id']}, {'$set': {
            'current_activity_idx': kwargs['current_activity_idx'],
            'total_activities': kwargs['total_activities']
        }}, upsert=True)
    elif event_type == 'activities_identified':
        ids = []
        for a in kwargs['activities']:
            ids.append(a.id)
        c.comparisons.update({'_id': kwargs['id']}, {'$set': {
            'activity_ids': ids
        }}, upsert=True)
    elif event_type == 'match':
        c.comparisons.update({'_id': kwargs['id']}, {'$push': { 'comparisons': kwargs['effort'] } }, upsert=True)
    elif event_type == 'complete':
        c.comparisons.update({'_id': kwargs['id']}, {'$set': {
            'state': 'Completed',
            'completed_ts': kwargs['completed_ts']
        }}, upsert=True)
    elif event_type == 'error':
        c.comparisons.update({'_id': kwargs['id']}, {'$set': {
            'state': 'Error',
            'completed_ts': kwargs['completed_ts'],
            'error_message': kwargs['error_message']
        }}, upsert=True)

    else:
        return

def task_listener_compare(worker, job):
    try:
        jd = json.loads(job.data)
        log.info('received job: {job}'.format(job=str(job)))

        # create our basic document if it doesn't exist
        comparison = c.comparisons.find_one({'_id': ObjectId(jd['id'])})

        ct = StravaCompare(
            athlete_id=jd['athlete_id'],
            compare_to_athlete_id=jd['compare_to_athlete_id'],
            access_token=jd['access_token'],
            id=comparison['_id'],
            callback=handle_event
        )

        if 'activity_ids' in jd:
            ct.compare(days=None, activity_ids=jd['activity_ids'])
        else:
            ct.compare(days=jd['days'])

    except:
        print 'error'
        log.exception('job failed')

        print 'error again'
        c.comparisons.update({'_id': ObjectId(jd['id'])}, {'$set': {
            'state': 'Error',
            'completed_ts': int(time()),
            'error_message': traceback.extract_tb()
        }}, upsert=True)

    print 'all done'
    return json_util.dumps(comparison['_id'])

try:
    log.info('registering StravaCompare worker with gearmand: %s', str(c.gmworker))
    c.gmworker.set_client_id('StravaCompare')
    c.gmworker.register_task('StravaCompare', task_listener_compare)

    log.info('starting worker')
    c.gmworker.work()
except:
    log.exception('error starting StravaCompare worker')
    raise

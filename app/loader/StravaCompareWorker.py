__author__ = 'ssteveli'

import gearman
from StravaCompare import StravaCompare
from bson import json_util, ObjectId
import json
import traceback
from pymongo import MongoClient
import urllib2
from time import time

client = MongoClient('strava-mongodb', 27017)
db = client.stravasocial
comparisons = db.comparisons
gmworker = gearman.GearmanWorker(['strava-gearmand:4730'])

def handle_event(event_type, **kwargs):
    if event_type == 'started':
        comparisons.update({'_id': kwargs['id']}, {'$set': {
            'state': 'Running',
            'started_ts': kwargs['started_ts']
        }}, upsert=True)
    elif event_type == 'activity':
        comparisons.update({'_id': kwargs['id']}, {'$set': {
            'current_activity_idx': kwargs['current_activity_idx'],
            'total_activities': kwargs['total_activities']
        }}, upsert=True)
    elif event_type == 'match':
        comparisons.update({'_id': kwargs['id']}, {'$push': { 'comparisons': kwargs['effort'] } }, upsert=True)
    elif event_type == 'complete':
        comparisons.update({'_id': kwargs['id']}, {'$set': {
            'state': 'Completed',
            'completed_ts': kwargs['completed_ts']
        }}, upsert=True)
    elif event_type == 'error':
        comparisons.update({'_id': kwargs['id']}, {'$set': {
            'state': 'Error',
            'completed_ts': kwargs['completed_ts'],
            'error_message': kwargs['error_message']
        }}, upsert=True)

    else:
        return

def task_listener_compare(worker, job):
    print 'received job: {job}'.format(job=str(job))
    try:
        jd = json.loads(job.data)

        # create our basic document if it doesn't exist
        c = comparisons.find_one({'_id': ObjectId(jd['id'])})

        ct = StravaCompare(
            athlete_id=jd['athlete_id'],
            compare_to_athlete_id=jd['compare_to_athlete_id'],
            access_token=jd['access_token'],
            id=c['_id'],
            callback=handle_event
        )
        try:
            ct.compare(days=jd['days'])
        except urllib2.HTTPError as e:
            handle_event('error', completed_ts=int(time.time()), error_message=e.message)

        return json_util.dumps(c['_id'])
    except:
        print 'job error: {error}'.format(error=traceback.format_exc())
        raise

print 'registering gearman StravaCompare task'
gmworker.set_client_id('StravaCompare')
gmworker.register_task('StravaCompare', task_listener_compare)

print 'starting StravaCompare worker'
gmworker.work()

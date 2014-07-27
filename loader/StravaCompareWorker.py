__author__ = 'ssteveli'

import gearman
from StravaCompare import StravaCompare
import json
import traceback
from pymongo import MongoClient

client = MongoClient('mongodb1', 27017)
db = client.stravasocial
comparisons = db.comparisons
gmworker = gearman.GearmanWorker(['192.168.59.103:4730'])

def task_listener_compare(worker, job):
    print 'received job: {job}'.format(job=str(job))
    try:
        jd = json.loads(job.data)
        ct = StravaCompare(jd['athlete_id'], jd['compare_to_athlete_id'], jd['access_token'])

        comparison = ct.compare()
        jd['result'] = json.dumps(comparison)

        comparisons.insert(comparison)

        return json.dumps(jd)
    except:
        print 'job error: {error}'.format(error=traceback.format_exc())
        raise

print 'registering gearman StravaCompare task'
gmworker.set_client_id('StravaCompare')
gmworker.register_task('StravaCompare', task_listener_compare)

print 'starting StravaCompare worker'
gmworker.work()
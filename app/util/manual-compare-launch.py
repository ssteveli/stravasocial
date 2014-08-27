__author__ = 'ssteveli'

import pyconfig
import time
from pymongo import MongoClient
from gearman import GearmanClient
import json
from json import dumps

athlete_id = 243490
access_token  = '3524f1573f2d982d901e4034f64f1324d503e38d'
compare_to_athlete_id = 116489
days = 10

client = MongoClient(pyconfig.get('mongodb.host', 'strava-mongodb'), int(pyconfig.get('mongodb.port', '27017')))
db = client.stravasocial
comparisons = db.comparisons
gearman = GearmanClient(['192.168.59.103:4730'])

# create our db record
c = {
    'athlete_id': athlete_id,
    'submitted_ts': int(time.time()),
    'state': 'Submitted',
    'compare_to_athlete_id': compare_to_athlete_id,
    'comparisons': [],
    'days': days
}

_id = comparisons.insert(c)

# now it's time to launch the gearman background job
job_details = {
    'athlete_id': athlete_id,
    'compare_to_athlete_id': compare_to_athlete_id,
    'access_token': access_token,
    'id': str(_id),
    'submitted_ts': int(time.time()),
    'state': 'Submitted',
    'days': days
}

print 'job created {}'.format(dumps(job_details))
job_request = gearman.submit_job('StravaCompare', json.dumps(job_details), background=True)
comparisons.update({'_id': _id}, {'$set': {'job_id': job_request.job.unique}})
print 'job request created {}'.format(str(job_request))


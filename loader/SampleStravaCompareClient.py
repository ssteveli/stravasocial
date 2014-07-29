
import gearman
import json
print 'creating gearman client'
gmclient = gearman.GearmanClient(['strava-gearmand:4730'])

jd = {
    'athlete_id': 2298968,
    #'compare_to_athlete_id': 2485249, #wendy
    #'compare_to_athlete_id': 387103, #ben
    'compare_to_athlete_id': 154952, #brian
   'access_token': '7f8e5ab7ec53926c6165c96d64a22a589d8c48b6'
}

print 'submitting job: {job}'.format(job = str(jd))
result = gmclient.submit_job('StravaCompare', json.dumps(jd), background=False)
print 'job successfully submitted {result}'.format(result = str(result))
print 'exception: {ex}'.format(ex=result.exception)

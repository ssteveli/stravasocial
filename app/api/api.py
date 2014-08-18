#!/usr/local/bin/python

from flask import Flask, jsonify, abort, make_response, Response, request
from pymongo import MongoClient
from bson.json_util import dumps, ObjectId
from gearman import GearmanClient, admin_client
from plans import Plan
from features import FeatureFlags
import time
import json
import pyconfig
from stravadao.strava import Strava
from util.idgenerator import IdGenerator
import datetime
import urllib
from datetime import date, timedelta

app = Flask(__name__)
idgen = IdGenerator()

class Container():
    def __init__(self):
        self.reload()

    @pyconfig.reload_hook
    def reload(self):
        self.client = MongoClient(pyconfig.get('mongodb.host', 'strava-mongodb'), int(pyconfig.get('mongodb.port', '27017')))
        self.db = self.client.stravasocial
        self.comparisons = self.db.comparisons
        self.authorizations = self.db.authorizations
        self.roles = self.db.roles

        self.gearman_connections = [
            'strava-gearmand:4730'
        ]
        self.gearmanClient = GearmanClient(self.gearman_connections)
        self.ff = FeatureFlags()

con = Container()

@app.errorhandler(401)
def unauthorized(error):
    return make_response(jsonify({'error': 'unauthorized', 'message': error.description}), 401)

@app.errorhandler(404) 
def not_found(error):
    return make_response(jsonify({'error': 'not found', 'message': error.description}), 404)

@app.errorhandler(400)
def invalid_request(error):
    return make_response(jsonify({'error': 'invalid request', 'message': error.description}), 400)

@app.errorhandler(403)
def forbidden(error):
    return make_response(jsonify({'error': 'forbidden', 'message': error.description}), 403)

@app.route('/api/strava/comparisons', methods=['POST'])
def launchComparison():
    req = request.get_json()
    athlete = validateSessionAndGetAthlete()

    if not con.ff.isOn('comparisons', default=True):
        abort(403, 'comparisons are currently turned off')

    if 'days' not in req and 'activity_ids' not in req:
        req['days'] = 1

    if 'days' in req and (req['days'] < 0 or req['days'] > 10):
        abort(403, 'invalid days value, must be between 1 and 10')

    if 'compare_to_athlete_id' not in req or get_stravadao().get_athlete(req['compare_to_athlete_id']) is None:
        abort(403, 'athlete to compare against is missing or was not found')

    if 'days' not in req and len(req['activity_ids']) == 0:
        abort(403, 'no activity ids or days parameter specified')

    if athlete['athlete_id'] == req['compare_to_athlete_id']:
        abort(403, 'you want to compare against yourself?')

    if is_comparison_allowed(athlete):
        # create our db record
        c = {
            'athlete_id': athlete['athlete_id'],
            'submitted_ts': int(time.time()),
            'state': 'Submitted',
            'compare_to_athlete_id': req['compare_to_athlete_id'],
            'comparisons': []
        }

        if 'days' in req:
            c['days'] = req['days']

        if 'activity_ids' in req:
            c['activity_ids'] = req['activity_ids']

        _id = con.comparisons.insert(c)

        # now it's time to launch the gearman background job
        job_details = {
            'athlete_id': athlete['athlete_id'],
            'compare_to_athlete_id': req['compare_to_athlete_id'],
            'access_token': athlete['access_token'],
            'id': str(_id),
            'submitted_ts': int(time.time()),
            'state': 'Submitted'
        }

        if 'days' in req:
            job_details['days'] = req['days']

        if 'activity_ids' in req:
            job_details['activity_ids'] = req['activity_ids']

        print 'job {}'.format(dumps(job_details))
        job_request = con.gearmanClient.submit_job('StravaCompare', json.dumps(job_details), background=True)
        con.comparisons.update({'_id': _id}, {'$set': {'job_id': job_request.job.unique}})
        c['job_id'] = job_request.job.unique
        c['id'] = str(c['_id'])
        c.pop('_id')

        return Response(dumps(c), mimetype='application/json', status=201, headers={'Location':'/api/strava/comparisons/' + c['id']})
    else:
        abort(403, 'no comparison is allowed at this time')

@app.route('/api/strava/comparisons')
def getComparisonsBySession():
    athlete = validateSessionAndGetAthlete()

    result = []

    is_admin = is_role('admin')
    q = {'athlete_id': athlete['athlete_id']} if not is_admin else {}
    #results = con.comparisons.find(q)

    agg = con.comparisons.aggregate([
        {'$match': q},
        {'$unwind': '$comparisons'},
        {'$group': {
            '_id': {
                '_id': '$_id',
                'athlete_id': '$athlete_id',
                'compare_to_athlete_id': '$compare_to_athlete_id',
                'started_ts': '$started_ts',
                'completed_ts': '$completed_ts',
                'state': '$state'
            },
            'comparisons_count': {'$sum': 1}
        }}
    ])

    running = False
    for r in agg['result']:
        x = r['_id']
    #for x in results:
        if 'compare_to_athlete_id' in x:
            x['id'] = str(x['_id'])
            x['comparisons_count'] = r['comparisons_count']
            #x['comparisons_count'] = len(x['comparisons'])
            if is_admin:
                x['viewtype'] = 'admin'
            x['compare_to_athlete'] = get_athlete_dict(x['compare_to_athlete_id'])
            x['athlete'] = get_athlete_dict(x['athlete_id'])

            if 'state' in x:
                if x['state'] == 'Running' or x['state'] == 'Submitted':
                    running = True

            result.append(x)
        else:
            print 'comparison is invalid, does not contain compare_to_athlete_id: {}'.format(dumps(x))

    return Response(dumps(result),
        mimetype='application/json',
        headers={
            'cache-control': 'no-cache'
        })

@app.route('/api/strava/comparisons/<comparison_id>', methods=['DELETE'])
def deleteComparison(comparison_id):
    athlete = validateSessionAndGetAthlete()
    try:
        _id = ObjectId(str(comparison_id))
        comparison = con.comparisons.find_one({'_id': ObjectId(str(comparison_id))})

        if comparison is None or (athlete['athlete_id'] != comparison['athlete_id'] and not is_role('admin')):
            abort(404, 'the specified comparison id was not found')

        con.comparisons.remove({'_id': ObjectId(str(comparison_id))})
        return make_response(jsonify({'message': 'comparison successfully deleted'}), 200)

    except:
        abort(400, 'invalid comparison id')

@app.route('/api/strava/comparisons/<comparisonid>')
def getComparisonBySession(comparisonid):
    athlete = validateSessionAndGetAthlete()

    _id = ObjectId(str(comparisonid))
    comparison = con.comparisons.find_one({'_id': ObjectId(str(comparisonid))})

    if comparison is None or (athlete['athlete_id'] != comparison['athlete_id'] and not is_role('admin')):
        abort(404, 'the specified comparison id was not found')

    comparison['compare_to_athlete'] = get_athlete_dict(comparison['compare_to_athlete_id'])
    comparison['id'] = str(comparison['_id'])
    comparison.pop('_id')
    comparison['url'] = request.path

    if 'state' not in comparison:
        comparison['state'] = 'Unknown'

    return Response(dumps(comparison),
        mimetype='application/json',
        headers={
           'cache-control': 'max-age=300' if comparison['state'] == 'Completed' else 'no-cache'
        })

@app.route('/api/strava/athlete')
def getAthleteBySession():
    athlete = validateSessionAndGetAthlete()
    return getAthlete(athlete['athlete_id'])

@app.route('/api/strava/athletes/<id>')
def getAthlete(id):
    requested_athlete = get_athlete_dict(id)

    if requested_athlete is None:
        abort(404, 'the specified athlete {} was not found'.format(id))

    return Response(json.dumps(requested_athlete),
        mimetype='application/json',
        headers={
            'cache-control': 'max-age=60'
        })

@app.route('/api/strava/athletes/<id>/clearcache', methods=['POST'])
def clear_athlete_cache(id):
    get_stravadao().invalidate_cached_athlete(id)
    return Response(dumps({'result': True}), mimetype="application/json")


def get_athlete_dict(id):
    requested_athlete = get_stravadao().get_athlete(id)

    if requested_athlete is None:
        return None
    else:
        return {
            'id': requested_athlete.id,
            'firstname': requested_athlete.firstname,
            'lastname': requested_athlete.lastname,
            'measurement_preference': requested_athlete.measurement_preference,
            'profile': requested_athlete.profile
        }

@app.route('/api/strava/athlete/plan')
def getAthletePlan():
    current_athlete = validateSessionAndGetAthlete()

    p = Plan(current_athlete)
    return Response(dumps(p.get_plan()),
        mimetype='application/json',
        headers={
            'cache-control': 'max-age=60'
        })

@app.route('/api/strava/activities')
def get_activities():
    athlete = validateSessionAndGetAthlete()

    activities = get_stravadao().get_activities(athlete['athlete_id'], date.today()-timedelta(days=360))

    results = []
    for a in activities:
        results.append({
            'id': a.id,
            'name': a.name,
            'start_date_local': str(a.start_date_local),
            'distance': int(a.distance)
        })

    results.sort(key=lambda x: x['start_date_local'], reverse=True)

    return Response(dumps(results),
        mimetype='application/json',
        headers={
            'cache-control': 'max-age=120'
        })

@app.route('/api/strava/authorization')
def createAuthorization():
        id = idgen.getId()
        redirect_url = request.args.get('redirect_uri')

        if redirect_url is None:
            abort(400, 'no redirect_uri parameter provided')

        params = {
                  'client_id': pyconfig.get('strava.client_id'),
                  'redirect_uri': redirect_url,
                  'response_type': 'code',
                  'scope': 'public',
                  'approval_prompt': 'force',
                  'state': id
        }

        auth = {
                'id': id,
                'url': 'https://www.strava.com/oauth/authorize?{params}'.format(params=urllib.urlencode(params)),
                'createdTs': datetime.datetime.utcnow()
        }
        con.authorizations.insert(auth)

        return Response(dumps({
            'id': auth['id'],
            'url': auth['url'],
            'createdTs': str(auth['createdTs'])
        }), mimetype='application/json')

@app.route('/api/strava/authorizations/<id>', methods=['PUT'])
def updateAuthentication(id):
    req_json = request.get_json()

    auth = con.authorizations.find_one({'id': id})

    if auth is None:
        abort(404, 'authorization {} not found'.format(id))

    if 'code' not in req_json:
        abort(403, 'field code is missing from the request json body')

    token = get_stravadao().exchange_code_for_token(req_json['code'])
    athlete = get_stravadao().set_access_token_and_get_athlete(token)

    auth['access_token'] = token
    auth['lastModifiedTs'] = datetime.datetime.utcnow()
    auth['athlete_id'] = athlete.id

    con.authorizations.save(auth)

    return Response(dumps({
        'id': auth['id'],
        'url': auth['url'],
        'createdTs': str(auth['createdTs']),
        'lastModifiedTs': str(auth['lastModifiedTs']),
        'code': req_json['code']
    }), mimetype="application/json")

@app.route('/api/strava/authorizations/session', methods=['DELETE'])
def deleteAuthentication():
    session_id = request.cookies.get('stravaSocialSessionId')

    if session_id is not None:
        authorization = con.authorizations.find_one({'id': session_id})

        if authorization is not None:
            get_stravadao().invalidate_cached_athlete(authorization['athlete_id'])
            con.authorizations.remove({'id': session_id})

    return Response(dumps({'result': True}), mimetype="application/json")

@app.route('/api/strava/authorizations/<id>/isvalid')
def validSession(id):
    validateSessionAndGetAthlete()
    return Response(dumps({'result': True}), mimetype="application/json")

@app.route('/api/admin/stats')
def getStats():
    stats = {
        'comparisons': con.db.comparisons.count(),
        'athletes': con.db.athletes.count(),
        'authorizations': {
            'total': con.db.authorizations.count(),
            'with_access_tokens': con.db.athletes.find({'access_token': { '$ne': None }}).count()
        }
    }
    return Response(json.dumps(stats),
        mimetype='application/json',
        headers={
            'cache-control': 'no-cache'
        })

def validateSessionAndGetAthlete():
    session_id = request.cookies.get('stravaSocialSessionId')

    if session_id is None:
        abort(401, 'no authorization information received')

    authorization = con.authorizations.find_one({'id': session_id})

    if authorization is None:
        abort(401, 'missing authorization received')

    if 'access_token' not in authorization:
        abort(403, 'authorization session is not complete, missing access token from Strava API')

    if 'athlete_id' not in authorization:
        abort(403, 'authorization session is not complete, missing athlete information')

    athlete = get_stravadao().get_athlete(authorization['athlete_id'])

    if athlete is None:
        abort(404, 'athlete not found')

    return {
        'athlete_id': authorization['athlete_id'],
        'access_token': authorization['access_token']
    }

@app.route('/api/admin/featureFlags')
def get_feature_flags():
    return Response(dumps(con.ff.get_all_features()), mimetype='application/json')

@app.route('/api/admin/featureFlags/<feature>')
def get_feature_flag(feature):
    return Response(str(con.ff.isOn(feature)).lower(), mimetype='text/plain')

@app.route('/api/admin/featureFlags/<feature>/turnOff', methods=['POST'])
def turn_feature_off(feature):
    con.ff.turnOff(feature)
    return Response(str(con.ff.isOn(feature)).lower(), mimetype='text/plain')

@app.route('/api/admin/featureFlags/<feature>/turnOn', methods=['POST'])
def turn_feature_on(feature):
    con.ff.turnOn(feature)
    return Response(str(con.ff.isOn(feature)).lower(), mimetype='text/plain')

@app.route('/api/admin/gearman/status')
def get_gearman_status():
    ac = admin_client.GearmanAdminClient(con.gearman_connections)
    return Response(dumps(ac.get_status()), mimetype='application/json')

def is_comparison_allowed(athlete):
    p = Plan(athlete).get_plan()
    if 'is_execution_allowed' not in p:
        return False
    else:
        return p['is_execution_allowed']

def is_role(role):
    if role is None:
        return False

    session_id = request.cookies.get('stravaSocialSessionId')

    if session_id is None:
        return False

    authorization = con.authorizations.find_one({'id': session_id})

    if authorization is None or 'athlete_id' not in authorization:
        return False

    i = con.roles.find({'role': role, 'athletes': authorization['athlete_id']}).count()
    return i > 0

def get_stravadao():
    token = None

    auth_header = request.headers.get('Authorization')
    if auth_header is not None:
        token = auth_header.rsplit(' ', 1)[1]
    else:
        session_id = request.cookies.get('stravaSocialSessionId')

        if session_id is not None:
            authorization = con.authorizations.find_one({'id': session_id})

            if authorization is not None and 'access_token' in authorization:
                token = authorization['access_token']

    return Strava(token)

if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug = True)

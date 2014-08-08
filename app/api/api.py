#!/usr/local/bin/python

from flask import Flask, jsonify, abort, make_response, Response, request
from strava import Strava
from pymongo import MongoClient
from bson.json_util import dumps, ObjectId
from gearman import GearmanClient, admin_client
from plans import Plan
from features import FeatureFlags
import time
import json
import pyconfig

app = Flask(__name__)
strava = Strava()

class Container():
    def __init__(self):
        self.reload()

    @pyconfig.reload_hook
    def reload(self):
        self.client = MongoClient(pyconfig.get('mongodb.host', 'strava-mongodb'), int(pyconfig.get('mongodb.port', '27017')))
        self.db = self.client.stravasocial
        self.comparisons = self.db.comparisons
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

    if 'days' not in req:
        req['days'] = 1

    if req['days'] < 0 or req['days'] > 10:
        abort(403, 'invalid days value, must be between 1 and 10')

    if 'compare_to_athlete_id' not in req or strava.getAthlete(athlete, req['compare_to_athlete_id']) is None:
        abort(403, 'athlete to compare against is missing or was not found')

    if athlete['id'] == req['compare_to_athlete_id']:
        abort(403, 'you want to compare against yourself?')

    if is_comparison_allowed(athlete):
        # create our db record
        c = {
            'athlete_id': athlete['id'],
            'compare_to_athlete_id': req['compare_to_athlete_id'],
            'comparisons': []
        }
        _id = con.collections['comparisons'].insert(c)

        # now it's time to launch the gearman background job
        job_details = {
            'athlete_id': athlete['id'],
            'compare_to_athlete_id': req['compare_to_athlete_id'],
            'access_token': athlete['access_token'],
            'days': req['days'],
            'id': str(_id),
            'submitted_ts': int(time.time()),
            'state': 'Submitted'
        }
        job_request = con.gearmanClient.submit_job('StravaCompare', json.dumps(job_details), background=True)
        con.collections['comparisons'].update({'_id': _id}, {'$set': {'job_id': job_request.job.unique}})
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
    for r in con.collections['comparisons'].find({'athlete_id': athlete['id']}):
        r['compare_to_athlete'] = strava.getAthlete(athlete, r['compare_to_athlete_id'])
        r['id'] = str(r['_id'])
        r.pop('_id')
        result.append(r)

    return Response(dumps(result), mimetype='application/json')

@app.route('/api/strava/comparisons/<comparison_id>', methods=['DELETE'])
def deleteComparison(comparison_id):
    athlete = validateSessionAndGetAthlete()
    try:
        _id = ObjectId(str(comparison_id))
        comparison = con.collections['comparisons'].find_one({'_id': ObjectId(str(comparison_id))})

        if comparison is None or athlete['id'] != comparison['athlete_id']:
            abort(404, 'the specified comparison id was not found')

        con.collections['comparisons'].remove({'_id': ObjectId(str(comparison_id))})
        return make_response(jsonify({'message': 'comparison successfully deleted'}), 200)

    except:
        abort(400, 'invalid comparison id')

@app.route('/api/strava/comparisons/<comparisonid>')
def getComparisonBySession(comparisonid):
    athlete = validateSessionAndGetAthlete()
    try:
        _id = ObjectId(str(comparisonid))
        comparison = con.collections['comparisons'].find_one({'_id': ObjectId(str(comparisonid))})

        if comparison is None or athlete['id'] != comparison['athlete_id']:
            abort(404, 'the specified comparison id was not found')

        comparison['compare_to_athlete'] = strava.getAthlete(athlete['id'], comparison['compare_to_athlete_id'])
        comparison['id'] = str(comparison['_id'])
        comparison.pop('_id')
        comparison['url'] = request.path

        return Response(dumps(comparison), mimetype='application/json')
    except:
        abort(400, 'invalid comparison id')

@app.route('/api/strava/athlete')
def getAthleteBySession():
    athlete = validateSessionAndGetAthlete()
    return Response(json.dumps(athlete), mimetype='application/json')

@app.route('/api/strava/athletes/<id>')
def getAthlete(id):
    current_athlete = validateSessionAndGetAthlete()

    requested_athlete = strava.getAthlete(current_athlete, id)

    if requested_athlete is None:
        abort(404)
    else:
        return Response(json.dumps(requested_athlete), mimetype='application/json')

@app.route('/api/strava/athlete/plan')
def getAthletePlan():
    current_athlete = validateSessionAndGetAthlete()

    p = Plan(current_athlete)
    return Response(dumps(p.get_plan()), mimetype='application/json')

@app.route('/api/strava/authorization')
def createAuthorization():
    return json.dumps(strava.createAuthorization(request.args.get('redirect_uri')))

@app.route('/api/strava/authorizations/<id>', methods=['PUT'])
def updateAuthentication(id):
    req_json = request.get_json()
    return json.dumps(strava.updateAuthorization(id, req_json['code']))

@app.route('/api/strava/authorizations/<id>', methods=['DELETE'])
def deleteAuthentication(id):
    strava.deleteAuthorization(id)
    return make_response(jsonify({'result': True}), 200)

@app.route('/api/strava/authorizations/<id>/isvalid')
def validSession(id):
    return json.dumps(strava.isAuthenticated(id))

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
    return Response(json.dumps(stats), mimetype='application/json')

def validateSessionAndGetAthlete():
    sessionId = request.cookies.get('stravaSocialSessionId')

    if sessionId is None:
        abort(401, 'no authorization information received')

    authorization = strava.getAuthorization(sessionId)

    if authorization is None:
        abort(401, 'missing authorization received')

    if 'access_token' not in authorization:
        abort(403, 'authorization session is not complete, missing access token from Strava API')

    if 'athlete_id' not in authorization:
        abort(403, 'authorization session is not complete, missing athlete information')

    athlete = strava.getAthleteFromStore(authorization['athlete_id'])

    if athlete is None:
        abort(404, 'athlete not found')

    athlete['access_token'] = authorization['access_token']
    return athlete

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

if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug = True)

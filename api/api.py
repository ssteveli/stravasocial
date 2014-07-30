#!/usr/local/bin/python

from flask import Flask, jsonify, abort, make_response, Response, request
from strava import Strava
from pymongo import MongoClient
from bson.json_util import dumps, ObjectId
from gearman import GearmanClient

import json

app = Flask(__name__)
strava = Strava()
mongo = MongoClient('192.168.1.52', 27017)
gearmanClient = GearmanClient(['strava-gearmand:4730'])
db = mongo.stravasocial
comparisons = db.comparisons

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

    if 'days' not in req:
        req['days'] = 1

    if req['days'] < 0 or req['days'] > 10:
        abort(403, 'invalid days value, must be between 1 and 10')

    if 'compare_to_athlete_id' not in req or strava.getAthlete(athlete, req['compare_to_athlete_id']) is None:
        abort(403, 'athlete to compare against is missing or was not found')

    if is_comparison_allowed():
        # create our db record
        c = {
            'athlete_id': athlete['id'],
            'compare_to_athlete_id': req['compare_to_athlete_id'],
            'comparisons': []
        }
        _id = comparisons.insert(c)

        # now it's time to launch the gearman background job
        job_details = {
            'athlete_id': athlete['id'],
            'compare_to_athlete_id': req['compare_to_athlete_id'],
            'access_token': athlete['access_token'],
            'days': req['days'],
            'id': str(_id)
        }
        job_request = gearmanClient.submit_job('StravaCompare', json.dumps(job_details), background=True)
        comparisons.update({'_id': _id}, {'$set': {'job_id': job_request.job.unique}})
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
    for r in comparisons.find({'athlete_id': athlete['id']}):
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
        comparison = comparisons.find_one({'_id': ObjectId(str(comparison_id))})

        if comparison is None or athlete['id'] != comparison['athlete_id']:
            abort(404, 'the specified comparison id was not found')

        comparisons.remove({'_id': ObjectId(str(comparison_id))})
        return make_response(jsonify({'message': 'comparison successfully deleted'}), 200)

    except:
        abort(400, 'invalid comparison id')

@app.route('/api/strava/comparisons/<comparisonid>')
def getComparisonBySession(comparisonid):
    athlete = validateSessionAndGetAthlete()
    try:
        _id = ObjectId(str(comparisonid))
        comparison = comparisons.find_one({'_id': ObjectId(str(comparisonid))})

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

def is_comparison_allowed():
    return True

if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug = True)
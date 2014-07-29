#!/usr/local/bin/python

from flask import Flask, jsonify, abort, make_response, Response, request
from strava import Strava
from pymongo import MongoClient
from bson.json_util import dumps, ObjectId

import json

app = Flask(__name__)
strava = Strava()
mongo = MongoClient('192.168.1.52', 27017)
db = mongo.stravasocial
comparisons = db.comparisons

@app.errorhandler(404) 
def not_found(error):
    return make_response(jsonify({'error': 'not found', 'message': error.description}), 404)

@app.errorhandler(400)
def invalid_request(error):
    return make_response(jsonify({'error': 'invalid request', 'message': error.description}), 400)

@app.route('/api/strava/comparisons')
def getComparisonsBySession():
    athlete = validateSessionAndGetAthlete()
    return Response(dumps(comparisons.find({'athlete_id': athlete['id']})), mimetype='application/json')

@app.route('/api/strava/comparisons/<comparisonid>')
def getComparisonBySession(comparisonid):
    athlete = validateSessionAndGetAthlete()
    try:
        _id = ObjectId(str(comparisonid))
        comparison = comparisons.find_one({'_id': ObjectId(str(comparisonid))})

        if comparison is None or athlete['id'] != comparison['athlete_id']:
            abort(404, 'the specified comparison id was not found')

        return Response(dumps(comparison), mimetype='application/json')
    except:
        abort(400, 'invalid comparison id')

@app.route('/api/strava/athlete')
def getAthleteBySession():
    athlete = validateSessionAndGetAthlete()
    return Response(json.dumps(athlete), mimetype='application/json')

@app.route('/api/strava/athletes/<id>')
def getAthlete(id):
    athlete = strava.getAthlete(id)
     
    if athlete is None:
        abort(404)
    else:
        return Response(json.dumps(athlete), mimetype='application/json')
    
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

    athlete = strava.getAthlete(authorization['athlete_id'])

    if athlete is None:
        abort(404, 'athlete not found')

    return athlete

if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug = True)
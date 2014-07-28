#!/usr/bin/python

from flask import Flask, jsonify, abort, make_response
from flask import request
from strava import Strava

import json

app = Flask(__name__)
strava = Strava()

@app.errorhandler(404) 
def not_found(error):
    return make_response(jsonify({'error': 'not found'}), 404)

@app.route('/api/strava/athletes/<id>')
def getAthlete(id):
    athlete = strava.getAthlete(id)
     
    if athlete is None:
        abort(404)
    else:
        return json.dumps(athlete)

@app.route('/api/strava/athletes/<id>/loadactivities', methods=['POST'])
def loadAthleteActivites(id):
    athlete = strava.getAthlete(id)
     
    if athlete is None:
        abort(404)
    else:
        result = strava.startActivityLoad(id)
        return json.dumps({
            'id': result.state,
            'state': result.state
        })
    
@app.route('/api/strava/authorization')
def createAuthorization():
    return json.dumps(strava.createAuthorization(request.args.get('redirect_uri')))

@app.route('/api/strava/authorizations/<id>', methods=['PUT'])
def updateAuthentication(id):
    req_json = request.get_json()
    print 'request: ' + str(req_json)
    
    return json.dumps(strava.updateAuthorization(id, req_json['code']))

@app.route('/api/strava/authorizations/<id>', methods=['DELETE'])
def deleteAuthentication(id):
    strava.deleteAuthorization(id)
    return make_response(jsonify({'result': True}), 200)

@app.route('/api/strava/authorizations/<id>/isvalid')
def validSession(id):
    return json.dumps(strava.isAuthenticated(id))

if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug = True)
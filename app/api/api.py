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

from model import Athlete

import logging
import logging.handlers

from flask_jwt import JWT, jwt_required, current_user

log = logging.getLogger("stravacompare")
log.setLevel(logging.DEBUG)

file = logging.handlers.RotatingFileHandler('/data/log/stravacompare-api.log', backupCount=5)
file.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file.setFormatter(formatter)
log.addHandler(file)

app = Flask(__name__)
app.debug = bool(pyconfig.get('api.debug', 'True'))
app.config['SECRET_KEY'] = pyconfig.get('api.secret_key', 'xxx')
app.config['JWT_EXPIRATION_DELTA'] = timedelta(days=31)

if app.config['SECRET_KEY'] == 'xxx':
    log.warn("api.secret_key value is the default development value, please set it to something else")

jwt = JWT(app)

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

### setup is done, below is the api implementation

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

@jwt.authentication_handler
def authenticate(username, password):
    auth = con.authorizations.find_one({'id': username})

    if auth is None:
        abort(400, 'invalid credentials')

    try:
        token = get_stravadao().exchange_code_for_token(password)
    except:
        log.exception("error received from strava trying to exchange a code for an access_token")
        abort(400, 'invalid credentials, unable to get token from strava')

    athlete = get_stravadao().set_access_token_and_get_athlete(token)

    auth['code'] = password
    auth['access_token'] = token
    auth['lastModifiedTs'] = datetime.datetime.utcnow()
    auth['athlete_id'] = athlete.id

    con.authorizations.save(auth)

    sd = Strava(auth['access_token'])
    requested_athlete = sd.get_athlete(auth['athlete_id'])

    return Athlete(
        id=username,
        athlete_id=requested_athlete.id,
        firstname=requested_athlete.firstname,
        lastname=requested_athlete.lastname,
        measure_preference=requested_athlete.measurement_preference,
        profile=requested_athlete.profile
    )

@jwt.user_handler
def load_athlete(payload):
    auth = con.authorizations.find_one({'id': payload['user_id']})

    if auth is None:
        abort(400, 'invalid credentials')

    if 'access_token' not in auth:
        abort(400, 'invalid credentials, no access token available')

    sd = Strava(auth['access_token'])
    requested_athlete = sd.get_athlete(auth['athlete_id'])

    return Athlete(
        id=payload['user_id'],
        athlete_id=requested_athlete.id,
        firstname=requested_athlete.firstname,
        lastname=requested_athlete.lastname,
        measure_preference=requested_athlete.measurement_preference,
        profile=requested_athlete.profile,
        access_token=auth['access_token']
    )

@app.route('/api/strava/comparisons', methods=['POST'])
@jwt_required()
def launch_comparison():
    req = request.get_json()

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

    if current_user.athlete_id == req['compare_to_athlete_id']:
        abort(403, 'you want to compare against yourself?')

    if is_comparison_allowed(current_user.athlete_id):
        # create our db record
        c = {
            'athlete_id': current_user.athlete_id,
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
            'athlete_id': current_user.athlete_id,
            'compare_to_athlete_id': req['compare_to_athlete_id'],
            'access_token': current_user.access_token,
            'id': str(_id),
            'submitted_ts': int(time.time()),
            'state': 'Submitted'
        }

        if 'days' in req:
            job_details['days'] = req['days']

        if 'activity_ids' in req:
            job_details['activity_ids'] = req['activity_ids']

        log.info('job created {}'.format(dumps(job_details)))
        job_request = con.gearmanClient.submit_job('StravaCompare', json.dumps(job_details), background=True)
        con.comparisons.update({'_id': _id}, {'$set': {'job_id': job_request.job.unique}})
        c['job_id'] = job_request.job.unique
        c['id'] = str(c['_id'])
        c.pop('_id')

        log.info('job submitted {}'.format(dumps(c)))

        return Response(dumps(c), mimetype='application/json', status=201, headers={'Location':'/api/strava/comparisons/' + c['id']})
    else:
        abort(403, 'no comparison is allowed at this time')

@app.route('/api/strava/comparisons')
@jwt_required()
def get_comparisons():
    print 'getting comparisons: %s' % json.dumps(current_user)
    result = []

    is_admin = is_role('admin')
    q = {'athlete_id': current_user.athlete_id} if not is_admin else {}
    results = con.comparisons.find(q)

    # commented out because I get mongo to deal with an empty or missing comparisons array correctly
    # agg = con.comparisons.aggregate([
    #     {'$match': q},
    #     {'$project':{
    #             'numberOfComparisons': { '$size': '$comparisons' }
    #         }
    #     },
    #     {'$unwind': '$comparisons'},
    #     {'$group': {
    #         '_id': {
    #             '_id': '$_id',
    #             'athlete_id': '$athlete_id',
    #             'compare_to_athlete_id': '$compare_to_athlete_id',
    #             'started_ts': '$started_ts',
    #             'completed_ts': '$completed_ts',
    #             'state': '$state',
    #             'comparison_count': '$numberOfComparisons'
    #         },
    #         'comparisons_count': {'$sum': 1}
    #     }}
    # ])

    for r in results:
        if 'compare_to_athlete_id' in r:
            result.append({
                'id': str(r['_id']),
                'comparisons_count': len(r['comparisons']) if 'comparisons' in r else 0,
                'viewtype': 'admin' if is_admin else 'default',
                'compare_to_athlete_id': r['compare_to_athlete_id'],
                'compare_to_athlete': get_athlete_dict(r['compare_to_athlete_id']),
                'athlete_id': r['athlete_id'],
                'athlete': get_athlete_dict(r['athlete_id']),
                'state': r['state'] if 'state' in r else 'Unknown',
                'submitted_ts': r['submitted_ts'] if 'submitted_ts' in r else None,
                'started_ts': r['started_ts'] if 'started_ts' in r else None,
                'completed_ts': r['completed_ts'] if 'completed_ts' in r else None,
            })
        else:
            log.warn('comparison is invalid, does not contain compare_to_athlete_id: {}'.format(dumps(r)))

    return Response(dumps(result),
        mimetype='application/json',
        headers={
            'cache-control': 'no-cache'
        })

@app.route('/api/strava/comparisons/<comparison_id>', methods=['DELETE'])
@jwt_required()
def delete_comparison(comparison_id):
    try:
        _id = ObjectId(str(comparison_id))
        comparison = con.comparisons.find_one({'_id': ObjectId(str(comparison_id))})

        if comparison is None or (current_user.athlete_id != comparison['athlete_id'] and not is_role('admin')):
            abort(404, 'the specified comparison id was not found')

        con.comparisons.remove({'_id': ObjectId(str(comparison_id))})
        return make_response(jsonify({'message': 'comparison successfully deleted'}), 200)

    except:
        abort(400, 'invalid comparison id')

@app.route('/api/strava/comparisons/<comparisonid>')
@jwt_required()
def get_comparison_by_id(comparisonid):
    if comparisonid == 'undefined':
        abort(404, 'comparisonid of {} was not found'.format(comparisonid))

    _id = ObjectId(str(comparisonid))
    comparison = con.comparisons.find_one({'_id': ObjectId(str(comparisonid))})

    if comparison is None:
        abort(404, 'the specified comparison id {} was not found'.format(comparisonid))

    # if this isn't a public comparisons, then this athlete must be the originator
    if current_user.athlete_id != comparison['athlete_id'] and not is_role('admin'):
        abort(404, 'the specified comparison id {} was not found'.format(comparisonid))

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
@jwt_required()
def get_current_athlete():
    athlete = current_user
    athlete.access_token = None

    return Response(json.dumps(athlete), mimetype="application/json", headers={'cache-control': 'max-age=30'})

@app.route('/api/strava/athletes/<id>')
@jwt_required()
def get_athlete(id):
    requested_athlete = get_athlete_dict(id)

    if requested_athlete is None:
        abort(404, 'the specified athlete {} was not found'.format(id))

    return Response(json.dumps(requested_athlete),
        mimetype='application/json',
        headers={
            'cache-control': 'max-age=60'
        })

@app.route('/api/strava/athletes/<id>/clearcache', methods=['POST'])
@jwt_required()
def clear_athlete_cache(athlete_id):
    get_stravadao().invalidate_cached_athlete(athlete_id)
    return Response(dumps({'result': True}), mimetype="application/json")

def get_athlete_dict(athlete_id):
    requested_athlete = get_stravadao().get_athlete(athlete_id)

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
@jwt_required()
def get_athlete_plan():
    p = Plan(current_user.athlete_id)
    return Response(dumps(p.get_plan()),
        mimetype='application/json',
        headers={
            'cache-control': 'max-age=60'
        })

@app.route('/api/strava/activities')
@jwt_required()
def get_activities():
    activities = get_stravadao().get_activities(current_user.athlete_id, date.today()-timedelta(days=360))

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
def create_strava_authorization():
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

@app.route('/api/strava/authorizations/session', methods=['DELETE'])
@jwt_required()
def delete_strava_authorization():
    authorization = con.authorizations.find_one({'id': current_user.id})

    if authorization is not None:
        get_stravadao().invalidate_cached_athlete(current_user.id)
        con.authorizations.remove({'id': current_user.id})

    return Response(dumps({'result': True}), mimetype="application/json")

@app.route('/api/admin/stats')
def get_stats():
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

def is_comparison_allowed(athlete_id):
    p = Plan(athlete_id).get_plan()
    if 'is_execution_allowed' not in p:
        return False
    else:
        return p['is_execution_allowed']

def is_role(role):
    if role is None:
        return False

    i = con.roles.find({'role': role, 'athletes': current_user.athlete_id}).count()
    return i > 0

def get_stravadao():
    if current_user is not None and current_user.access_token is not None:
        return Strava(current_user.access_token)

    abort(403, 'no access token available for strava')

if __name__ == '__main__':
    app.run(host = '0.0.0.0')

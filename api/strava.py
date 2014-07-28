
from idgenerator import IdGenerator
from pymongo import MongoClient
import json
import urllib
import urllib2
import datetime
import gearman

idgen = IdGenerator()
client = MongoClient('192.168.1.52', 27017)
gearmanClient =  gearman.GearmanClient(['strava-gearmand:4730'])
db = client.stravasocial
authorizations = db.authorizations
athletes = db.athletes
activities = db.activities

class Strava:
    
    config = {}
    
    def __init__(self):
        with open('/data/stravasocial/api/config.json') as config_file:
            self.config = json.load(config_file)
        
    def startActivityLoad(self, id):
        auth = authorizations.find_one({'athlete_id': int(id)})
        
        if auth is not None:
            token = auth['access_token']
            return gearmanClient.submit_job('loadStravaActivities', json.dumps({'athlete_id': id, 'access_token': token}), background=True)
                                     
    def getAthlete(self, id):
        athlete = athletes.find_one({'id': int(id)})
        return athlete
    
    def isAuthenticated(self, id):
        auth = authorizations.find_one({'id': id})
        result = {
                  'is_valid': False
        }
        
        if auth is not None:
            if 'access_token' in auth:
                result['is_valid'] = True
                result['athlete_id'] = auth['athlete_id']
        
        return result

    def createAuthorization(self, redirectUrl):
        id = idgen.getId()
        
        params = {
                  'client_id': self.config['strava']['client_id'],
                  'redirect_uri': redirectUrl,
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
        authorizations.insert(auth)
        
        return {
                'id': auth['id'],
                'url': auth['url'],
                'createdTs': str(auth['createdTs'])
        }
    
    def deleteAuthorization(self, id):
        authorizations.remove({'id': id})
        
    def updateAuthorization(self, id, code):
        auth = authorizations.find_one({'id': id})
        
        params = urllib.urlencode({
                  'client_id': self.config['strava']['client_id'],
                  'client_secret': self.config['strava']['client_secret'],
                  'code': code
        })
        
        req = urllib2.Request('https://www.strava.com/oauth/token', params)
        req.add_header('Accept', 'application/json')
        
        resp = json.loads(urllib2.urlopen(req).read())
        print 'strava response: ' + str(resp)
        
        auth['code'] = code
        auth['lastModifiedTs'] = datetime.datetime.utcnow()
        auth['access_token'] = resp['access_token']
        auth['athlete_id'] = resp['athlete']['id']
        
        authorizations.save(auth)
        
        resp['athlete']['_id'] = resp['athlete']['id']       
        athletes.save(resp['athlete'])
        
        return {
                'id': auth['id'],
                'url': auth['url'],
                'createdTs': str(auth['createdTs']),
                'lastModifiedTs': str(auth['lastModifiedTs']),
                'code': auth['code']
        }

        
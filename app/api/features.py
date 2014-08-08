__author__ = 'ssteveli'

from pymongo import MongoClient
import pyconfig

class FeatureFlags:

    def __init__(self):
        self.reload()

    @pyconfig.reload_hook
    def reload(self):
        self.client = MongoClient(pyconfig.get('mongodb.host', 'strava-mongodb'), int(pyconfig.get('mongodb.port', '27017')))
        self.db = self.client.stravasocial
        self.features = self.db.features

    def isOn(self, feature, default=False):
        if feature is None:
            return default

        db_feature = self.features.find_one({'_id': feature})

        if db_feature is None:
            return default

        if 'active' not in db_feature:
            return default

        return db_feature['active']

    def turnOn(self, feature):
        if feature is None:
            return

        self.features.update({'_id': feature}, {'$set': { 'active': True }}, upsert=True)

    def turnOff(self, feature):
        if feature is None:
            return

        self.features.update({'_id': feature}, {'$set': { 'active': False }}, upsert=True)

    def get_all_features(self):
        return self.features.find({})

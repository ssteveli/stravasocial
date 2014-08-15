from stravalib import Client
from util.timing import timing
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
import pyconfig
from requests.exceptions import HTTPError

cache_opts = {
    'cache.type': pyconfig.get('cache.type', 'file'),
    'cache.data_dir': pyconfig.get('cache.data_dir', '/tmp/cache/data'),
    'cache.lock_dir': pyconfig.get('cache.lock_dir', '/tmp/cache/lock')
}

cache = CacheManager(**parse_cache_config_options(cache_opts))

class Strava():
    def __init__(self, access_token=None):
        self.client = Client()

        if access_token is not None:
            self.client.access_token = access_token

    @timing('strava_invalidate_cached_athlete')
    def invalidate_cached_athlete(self, id):
        cache.invalidate(self.get_athlete, 'strava_get_athlete', id)

    @timing('strava_set_access_token_and_get_athlete')
    def set_access_token_and_get_athlete(self, token):
        self.client.access_token = token
        return self.client.get_athlete()

    @timing('strava_exchange_code_for_token')
    def exchange_code_for_token(self, code):
        return self.client.exchange_code_for_token(
            client_id=pyconfig.get('strava.client_id'),
            client_secret=pyconfig.get('strava.client_secret'),
            code=code)

    @timing('strava_get_activities')
    @cache.cache('strava_get_activities', expire=3600)
    def get_activities(self, athlete_id, after):
        activities = []

        for a in list(self.client.get_activities(after=after)):
            activities.append(a)

        return activities

    @timing('strava_get_athlete')
    @cache.cache('strava_get_athlete', expire=3600)
    def get_athlete(self, athlete_id):
        try:
            return self.client.get_athlete(athlete_id)
        except HTTPError as e:
            # i don't know what's going on here, but the HTTPError I get back doesn't seem to have the
            # status code contained anywhere but the string message, argh!
            if e.message.startswith('404'):
                return None
            else:
                raise e

    @timing('strava_get_activity')
    @cache.cache('strava_get_activity')
    def get_activity(self, activity_id):
        print 'getting detailed activity for activityId: {activityId}'.format(activityId = activity_id)
        return self.client.get_activity(activity_id)

    @timing('strava_get_efforts')
    @cache.cache('strava_get_efforts', expire=3600)
    def get_efforts(self, segment_id, athlete_id, limit=1):
        print 'getting efforts for athlete {}, segment {}, limit {}'.format(athlete_id, segment_id, limit)

        efforts = []
        for effort in list(self.client.get_segment_efforts(segment_id, athlete_id, limit=limit)):
            efforts.append(effort)

        return efforts

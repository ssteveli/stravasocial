__author__ = 'ssteveli'

from datetime import date, timedelta
import time
from util.timing import timing

from stravadao.strava import Strava

class StravaCompare:

    def __init__(self, athlete_id=None, compare_to_athlete_id=None, access_token=None, id=None, callback=None):
        self.athlete_id = athlete_id
        self.compare_to_athlete_id = compare_to_athlete_id
        self.access_token = access_token
        self.id = id
        self.callback = callback
        self.sd = Strava(access_token)

    @timing('compare')
    def compare(self, days=1, activity_ids=None):
        print 'comparing {athlete_id} to {compare_to_athlete_id}'.format(athlete_id=self.athlete_id, compare_to_athlete_id=self.compare_to_athlete_id)

        result = {
            'started_ts': int(time.time()),
            'state': 'RUNNING',
            'athlete_id': self.athlete_id,
            'compare_to_athlete_id': self.compare_to_athlete_id,
            'comparisons': []
        }
        self.fireCallback('started', state='Running', started_ts=result['started_ts'])


        activities = []

        if days is not None:
            activities = self.getActivities(self.athlete_id, days=days)
        elif activity_ids is not None:
            for aid in activity_ids[:10]:
                activities.append(self.sd.get_activity(aid))

        count = 0
        for activity in activities:
            count = count + 1
            print 'processing activity {i} of {total}'.format(i=count, total=len(activities))
            self.fireCallback('activity', current_activity_idx=count, total_activities=len(activities))

            dactivity = self.sd.get_activity(activity.id)
            print 'i called getDetailedActivity asking for {} and got {} which has {} efforts'.format(activity.id, dactivity.id, list(dactivity.segment_efforts).__len__())

            ecount = 0
            for effort in list(dactivity.segment_efforts):
                ecount = ecount + 1
                print 'processing effort {i} of {total}'.format(i=ecount, total=len(list(dactivity.segment_efforts)))

                if self.segmentNotProcessedAlready(effort.segment.id, result['comparisons']):
                    cefforts = list(self.sd.get_efforts(effort.segment.id, self.compare_to_athlete_id))

                    if len(cefforts) > 0:
                        ceffort = cefforts.pop(0)

                        topefforts = list(self.sd.get_efforts(effort.segment.id, self.athlete_id))
                        topeffort = topefforts.pop(0)

                        e = {
                            'segment': {
                                'id': topeffort.segment.id,
                                'name': topeffort.name,
                                'average_grade': topeffort.segment.average_grade
                            },
                            'effort': {
                                'id': topeffort.id,
                                'athlete': {
                                    'id': topeffort.athlete.id
                                },
                                'activity': {
                                    'id': topeffort.activity.id,
                                    'name': topeffort.name
                                },
                                'moving_time': topeffort.moving_time.total_seconds(),
                                'elapsed_time': topeffort.elapsed_time.total_seconds(),
                                'distance': topeffort.distance.get_num(),
                                'average_watts': topeffort.average_watts,
                                'average_heartrate': topeffort.average_heartrate,
                                'max_heartrate': topeffort.max_heartrate,
                                'average_cadence': topeffort.average_cadence
                            },
                            'compared_to_effort': {
                                'id': ceffort.id,
                                'athlete': {
                                    'id': ceffort.athlete.id
                                },
                                'activity': {
                                    'id': ceffort.activity.id,
                                    'name': ceffort.activity.name
                                },
                                'moving_time': ceffort.moving_time.total_seconds(),
                                'elapsed_time': ceffort.elapsed_time.total_seconds(),
                                'distance': ceffort.distance.get_num(),
                                'average_watts': ceffort.average_watts,
                                'average_heartrate': ceffort.average_heartrate,
                                'max_heartrate': ceffort.max_heartrate,
                                'average_cadence': ceffort.average_cadence
                            }
                        }
                        result['comparisons'].append(e)
                        self.fireCallback('match', effort=e)
                    else:
                        print 'skipping effort {i}, segment {s} already processed'.format(i=ecount, s=effort.segment.id)

        result['state'] = 'COMPLETED'
        result['completed_ts'] = int(time.time())
        print 'completed execution in {duration}ms'.format(duration=(result['completed_ts']-result['started_ts']))
        self.fireCallback('complete', state='Completed', completed_ts=result['completed_ts'])
        return result


    def getActivities(self, athlete_id, days=31):
        print 'getting activities for the past {days} days'.format(days=days)
        activities = list(self.sd.get_activities(date.today()-timedelta(days=days)))
        print 'found {count} activities in the past {days} days'.format(count=len(activities), days=days)

        return activities

    def segmentNotProcessedAlready(self, segmentId, comparisons):
        for i in list(comparisons):
            if segmentId == i['segment']['id']:
                return False

        return True

    def fireCallback(self, type, **kwargs):
        if self.callback is None:
            return
        else:
            kwargs['id'] = self.id
            self.callback(type, **kwargs)

if __name__ == '__main__':
    print 'comparison result: {}'.format(StravaCompare(2298968, 2485249, '7f8e5ab7ec53926c6165c96d64a22a589d8c48b6').compare(days=3)) #wendy
    #print 'comparison result: {}'.format(StravaCompare(2298968, 387103, '7f8e5ab7ec53926c6165c96d64a22a589d8c48b6').compare(days=3)) #ben

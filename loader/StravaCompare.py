__author__ = 'ssteveli'

from stravalib import Client
from datetime import date, timedelta
import time
import json
import logging

logging.basicConfig(level=50)

class StravaCompare:
    client = Client()
    athleteId = -1
    compareToAthleteId = -1

    def __init__(self, athleteId, compareToAthleteId, accessToken):
        self.athleteId = athleteId
        self.compareToAthleteId = compareToAthleteId

        print 'building stravalib client with access_token {accessToken}'.format(accessToken=accessToken)
        self.client.access_token = accessToken

    def compare(self, days=3):
        print 'comparing {athleteId} to {compareToAthleteId}'.format(athleteId=self.athleteId, compareToAthleteId=self.compareToAthleteId)

        result = {
            'started_ts': int(time.time()),
            'state': 'RUNNING',
            'athlete_id': self.athleteId,
            'compare_to_athlete_id': self.compareToAthleteId,
            'comparisons': []
        }

        activities = self.getActivities(days=days)

        count = 0
        for activity in activities:
            count = count + 1
            print 'processing activity {i} of {total}'.format(i=count, total=len(activities))
            dactivity = self.getDetailedActivity(activity.id)

            ecount = 0
            for effort in list(dactivity.segment_efforts):
                ecount = ecount + 1
                print 'processing effort {i} of {total}'.format(i=ecount, total=len(list(dactivity.segment_efforts)))

                if self.segmentNotProcessedAlready(effort.segment.id, result['comparisons']):
                    cefforts = list(self.getEfforts(effort.segment.id, self.compareToAthleteId))

                    if len(cefforts) > 0:
                        ceffort = cefforts.pop(0)

                        topefforts = list(self.getEfforts(effort.segment.id, self.athleteId))
                        topeffort = topefforts.pop(0)

                        result['comparisons'].append({
                            'segment': {
                                'id': topeffort.segment.id,
                                'name': topeffort.name
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
                        })
                    else:
                        print 'skipping effort {i}, segment {s} already processed'.format(i=ecount, s=effort.segment.id)

        result['state'] = 'COMPLETED'
        result['completed_ts'] = int(time.time())
        print 'completed execution in {duration}ms'.format(duration=(result['completed_ts']-result['started_ts']))
        return result


    def getActivities(self, days=31):
        print 'getting activities for the past {days}'.format(days=days)
        activities = list(self.client.get_activities(after=date.today()-timedelta(days=days)))
        print 'found {count} activities in the past {days}'.format(count=len(activities), days=days)

        return activities

    def getDetailedActivity(self, activityId):
        print 'getting detailed activity for activityId: {activityId}'.format(activityId = activityId)
        return self.client.get_activity(activityId)

    def getEfforts(self, segmentId, athleteId):
        return self.client.get_segment_efforts(segmentId,athleteId,limit=1)

    def segmentNotProcessedAlready(self, segmentId, comparisons):
        for i in list(comparisons):
            if segmentId == i['segment']['id']:
                return False

        return True

if __name__ == '__main__':
    #StravaCompare(2298968, 2485249, '7f8e5ab7ec53926c6165c96d64a22a589d8c48b6').compare() #wendy
    StravaCompare(2298968, 387103, '7f8e5ab7ec53926c6165c96d64a22a589d8c48b6').compare() #ben


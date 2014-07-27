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

    def compare(self, days=31):
        print 'comparing {athleteId} to {compareToAthleteId}'.format(athleteId=self.athleteId, compareToAthleteId=self.compareToAthleteId)

        result = {
            'started_ts': int(time.time()),
            'state': 'RUNNING',
            'athlete_id': self.athleteId,
            'compare_to_athlete_id': self.compareToAthleteId,
            'comparisons': []
        }

        activities = self.getActivities(days=days)

        for activity in activities:
            dactivity = self.getDetailedActivity(activity.id)

            for effort in list(dactivity.segment_efforts):
                cefforts = list(self.getEfforts(effort.segment.id, self.compareToAthleteId))
                
                if len(cefforts) > 0:
                    ceffort = cefforts.pop(0)
                    result['comparisons'].append({
                        'segment': {
                            'id': effort.segment.id,
                            'name': effort.name
                        },
                        'efforts': [{
                            'id': effort.id,
                            'athlete': {
                                'id': effort.athlete.id  
                            },
                            'activity': {
                                'id': effort.activity.id,
                                'name': activity.name
                            },
                            'moving_time': effort.moving_time.total_seconds(),
                            'elapsed_time': effort.elapsed_time.total_seconds(),
                            'distance': effort.distance.get_num(),
                            'average_watts': effort.average_watts,
                            'average_heartrate': effort.average_heartrate,
                            'max_heartrate': effort.max_heartrate,
                            'average_cadence': effort.average_cadence
                        },{
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

                        }]
                    })
                    print '{comparison}'.format(comparison = json.dumps(result))

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


if __name__ == '__main__':
    StravaCompare(2298968, 2485249, '7f8e5ab7ec53926c6165c96d64a22a589d8c48b6').compare()

var appControllers = angular.module('appControllers', ['ipCookie']);

appControllers.controller('MainController', ['$scope', '$routeParams', '$http', 'ipCookie',
	function($scope, $routeParams, $http, ipCookie) {
        $scope.athlete = null;

        $http.get('/api/strava/athlete').
            success(function(data) {
                $scope.athlete = data;
            }).error(function(error) {
                console.log('athlete resource error: ' + error);
                $scope.athlete = null;
            });

		$scope.sendToStrava = function() {
			return_url = window.location.protocol + 
				'//' + 
				window.location.hostname + 
				'/stravareturn';
		
			$http.get('/api/strava/authorization?redirect_uri=' + return_url).
				success(function(data) {
					window.location.href = data.url;
				});
		};
		
		$scope.disconnect = function disconnect() {
			$http.delete('/api/strava/authorizations/' + $scope.sessionId).
				success(function(data) {
					$scope.athlete = null;
					ipCookie.remove('stravaSocialSessionId');
				});
		};	
	}
]);

appControllers.controller('StravaReturnController', ['$scope', '$location', '$http', 'ipCookie',
    function($scope, $location, $http, ipCookie) {
        $scope.code = $location.search()['code'];
        $scope.state = $location.search()['state'];
        $scope.error = $location.search()['error'];

        if (!$scope.error) {
            $http.put('/api/strava/authorizations/' + $scope.state, {'code':$scope.code})
                .success(function(data) {
                    ipCookie('stravaSocialSessionId', $scope.state, {expires:31, path: '/'});
                    window.location.href = '/';
                });
        }
    }
]);

appControllers.controller('ComparisonController', ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {
        $scope.comparisons = [];

        $http.get('/api/strava/comparisons').
            success(function(data) {
                data.sort(compare);
                $scope.comparisons = data;
            });

        function compare(a, b) {
            if (a.started_ts < b.started_ts)
                return 1;
            if (a.started_ts > b.started_ts)
                return -1;

            return 0;
        }

        $scope.deleteComparison = function(idx) {
            var record_to_delete = $scope.comparisons[idx];

            $http.delete('/api/strava/comparisons/' + record_to_delete.id).
                success(function(data) {
                    $scope.comparisons.splice(idx, 1);
                });
        }

        $scope.$on('newlaunch', function(event, data) {
            $scope.comparisons.unshift(data);
            $scope.info_message = 'Your comparison job has been successfully created and will process as soon as possible';
        });

        $scope.$on('errorlaunch', function(event, error) {
           console.log('error received: ', JSON.stringify(error));
           $scope.danger_message = error.message;
        });

        $scope.dismissDanger = function() {
            $scope.danger_message = null;
        }

        $scope.dismissInfo = function() {
            $scope.info_message = null;
        }
    }]);

appControllers.controller('NewComparisonController', ['$scope', '$http',
    function($scope, $http) {
        $scope.days_ago = 1;

        $scope.openLaunch = function() {
          $scope.showDialog = true;
        };

        $scope.closeLaunch = function() {
            $scope.showDialog = false;
        };

        $scope.submitLaunch = function() {
            $scope.showDialog = false;

            req = {
                'compare_to_athlete_id': $scope.compare_to_athlete_id,
                'days': $scope.days_ago
            };

            $http.post('/api/strava/comparisons', {
                'compare_to_athlete_id': $scope.compare_to_athlete_id,
                'days': $scope.days_ago
            }).success(function (data) {
                $scope.$emit('newlaunch', data);
            }).error(function(error) {
                console.log('error');
                $scope.$emit('errorlaunch', error);
            })
        };

        $scope.athleteIdChanged = function() {
            if ($scope.newcomparisonform.days_ago.$valid)
                $http.get('/api/strava/athletes/' + $scope.compare_to_athlete_id).
                    success(function (data) {
                        $scope.athlete_validation = 'Athlete ' + data.firstname + ' ' + data.lastname + ' found';
                    }).
                    error(function (error) {
                        $scope.athlete_validation = 'Athlete number ' + $scope.compare_to_athlete_id + ' was not found';
                    });
        };
    }]);

appControllers.controller('ComparisonDetailController', ['$scope', '$http', '$routeParams', '$timeout', '$location',
    function ($scope, $http, $routeParams, $timeout, $location) {
        $scope.comparison = {};
        $scope.location = $location;

          $http.get('/api/admin/featureFlags/socialSharing').
              success(function (data) {
                  if (data == 'true')
                    $scope.social_sharing = true;
                  else
                    $scope.social_sharing = false;
              }).
              error(function (error) {

              });

        var retrieveComparisons = function () {
            $http.get('/api/strava/comparisons/' + $routeParams.comparisonId).
                success(function (data) {
                    $scope.comparison = data;
                    var sum = 0;
                    var win = 0;
                    var loss = 0;
                    var tied = 0;
                    for (var i=0; i<data.comparisons.length; i++) {
                        var c = data.comparisons[i];
                        var diff = (c.compared_to_effort.moving_time - c.effort.moving_time);
                        sum += diff;
                        if (diff > 0) {
                            win++;
                        } else if (diff < 0) {
                            loss++;
                        } else {
                            tied++;
                        }
                    }
                    $scope.total_time_difference = sum;
                    $scope.wins = win;
                    $scope.losses = loss;
                    $scope.ties = tied;
                    $scope.chartData = [
                        {
                            'key': 'Wins',
                            'y': win
                        },{
                            'key': 'Losses',
                            'y': loss
                        },{
                            'key': 'Tied',
                            'y': tied
                        }
                    ];
                    if (data.state == 'Running') {
                        $timeout(retrieveComparisons, 1000)
                    }
                });
        }

        // initial retrieval
        retrieveComparisons();

        $scope.xFunction = function(){
            return function(d) {
                return d.key;
            };
        }

        $scope.yFunction = function(){
            return function(d) {
                return d.y;
            };
        }

        var colorArray = ['lightgreen', 'red', 'lightgray'];
        $scope.colorFunction = function() {
            return function(d, i) {
                return colorArray[i];
            };
        }
    }]);

function manageSession($scope, $http, ipCookie) {
    $scope.sessionId = ipCookie('stravaSocialSessionId');

    if ($scope.sessionId) {
        console.log('validating session ' + $scope.sessionId);
        $http.get('/api/strava/authorizations/' + $scope.sessionId + '/isvalid').
            success(function(data) {
                $scope.sessionIsValid = data.is_valid;

                $http.get('/api/strava/athletes/' + data.athlete_id).
                    success(function(data) {
                        $scope.athlete = data;
                    });
            });
    }
}

function handleMissingImage(image) {
    image.src = 'http://1.bp.blogspot.com/-An8klzluffQ/Ul8rhCqp29I/AAAAAAAAAi0/CzO4Tbe1nkk/s1600/no_image_small.png';
}
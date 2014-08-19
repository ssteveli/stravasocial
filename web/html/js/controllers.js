
var appControllers = angular.module('appControllers', ['ipCookie']);

var mp = undefined;

appControllers.controller('MainController', ['$scope', '$routeParams', '$http', 'ipCookie', '$window',
	function($scope, $routeParams, $http, ipCookie, $window) {
        $scope.athlete = null;

        $http.get('/api/strava/athlete').
            success(function(data) {
                $scope.athlete = data;

                if (mp == undefined) {
                    mp = data.measurement_preference;
                    $scope.measurement_preference = mp;
                } else {
                    $scope.measurement_preference = mp;
                }

                if ($window.ga)
                    $window.ga('set', '&uid', data.id);

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
			$http.delete('/api/strava/authorizations/session').
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

appControllers.controller('ComparisonController', ['$scope', '$http', '$routeParams', '$timeout', '$resource', '$filter', 'ngTableParams',
    function ($scope, $http, $routeParams, $timeout, $resource, $filter, ngTableParams) {
        $scope.loading = true;

        $scope.data = $resource('/api/strava/comparisons').query();
        $scope.data.$promise.then(function (data) {
            $scope.loading = false;
            $scope.tableParams = new ngTableParams({
                page: 1,
                count: 10,
                sorting: {
                    started_ts: 'dsc'
                }
            }, {
                total: 0,
                getData: function ($defer, params) {
                    var orderedData = params.sorting() ?
                        $filter('orderBy')(data, params.orderBy()) : data;
                    params.total(data.length);
                    $defer.resolve(orderedData.slice((params.page() - 1) * params.count(), params.page() * params.count()));
                }
            });
        });

        $scope.deleteComparison = function(id) {
            $http.delete('/api/strava/comparisons/' + id).
                success(function(data) {
                    for (var i=0; i<$scope.data.length; i++) {
                        if ($scope.data[i].id == id) {
                            $scope.data.splice(i, 1);
                            $scope.tableParams.reload();
                            break;
                        }
                    }
                }).
                error(function(error) {
                    $scope.danger_message = 'Sorry, there was some kind of error deleting the comparisons';
                });
        };

        $scope.$on('newlaunch', function(event, data) {
            $scope.data.unshift(data);
            $scope.tableParams.reload();
            $scope.info_message = 'Your comparison job has been successfully created and will process as soon as possible';
        });

        $scope.$on('errorlaunch', function(event, error) {
           console.log('error received: ', JSON.stringify(error));
           $scope.danger_message = error.message;
        });

        $scope.dismissDanger = function() {
            $scope.danger_message = null;
        };

        $scope.dismissInfo = function() {
            $scope.info_message = null;
        };
    }]);

appControllers.controller('NewComparisonController', ['$scope', '$http', '$resource', '$filter', 'ngTableParams',
    function($scope, $http, $resource, $filter, ngTableParams) {
        $http.get('/api/strava/athlete').
            success(function(data) {
                $scope.athlete = data;

                if (mp == undefined) {
                    mp = data.measurement_preference;
                    $scope.measurement_preference = mp;
                } else {
                    $scope.measurement_preference = mp;
                }

            }).error(function(error) {
                console.log('athlete resource error: ' + error);
                $scope.athlete = null;
            });

        $scope.days_ago = undefined;

        $scope.openLaunch = function() {
            $scope.$watch('acc2open', function() {
                if ($scope.acc2open) {
                    $scope.loading = true;
                    $scope.data = $resource('/api/strava/activities').query();
                    $scope.data.$promise.then(function (data) {
                        $scope.loading = false;
                        $scope.atableParams = new ngTableParams({
                            page: 1,
                            count: 10
                        }, {
                            total: 0,
                            getData: function ($defer, params) {
                                params.total(data.length);
                                $defer.resolve(data.slice((params.page() - 1) * params.count(), params.page() * params.count()));
                            }
                        });
                    });
                }
            });

            $http.get('/api/strava/athlete/plan').
                success(function (data) {
                    if (data.is_execution_allowed) {
                        $scope.showDialog = true;
                        $scope.isLaunchDisabled = false;
                    } else {
                        if (data.next_execution_code == "DISABLED")
                            $scope.$emit('errorlaunch', {'message': 'The ability to run comparisons is currently disabled, please try again later.'});
                        else if (data.next_execution_code == "ENFORCED_DELAY")
                            $scope.$emit('errorlaunch',
                                {'message':
                                    'Sorry, your account requires  ' +
                                    format_seconds(data.delay) +
                                    ' between comparisons, you must wait another ' +
                                    format_seconds(data.next_execution_time - (new Date().getTime()/1000))});
                        else if (data.next_execution_code == "JOB_RUNNING")
                            $scope.$emit('errorlaunch', {'message': 'Sorry, you have a comparison running which must complete first'});
                        $scope.isLaunchDisabled = true;
                    }
                }).
                error(function (data) {
                    $scope.$emit('errorlaunch', {'message': 'Sorry, comparisons are not allowed at this time'});
                });
        };

        $scope.closeLaunch = function() {
            $scope.showDialog = false;
        };

        $scope.selectedActivities = []

        $scope.changeSelection= function(activity) {
            if (activity.$selected) {
                $scope.selectedActivities.push(activity.id);
            } else {
                var idx = $scope.selectedActivities.indexOf(activity.id);
                if (idx > -1)
                    $scope.selectedActivities.splice(idx, 1);
            }
        }

        $scope.submitLaunch = function() {
            $scope.showDialog = false;

            var req = {
                'compare_to_athlete_id': $scope.compare_to_athlete_id
            };

            if ($scope.acc2open) {
                req.activity_ids = $scope.selectedActivities;
            } else {
                req.days = $scope.days_ago;
            }

            $http.post('/api/strava/comparisons', req).success(function (data) {
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

appControllers.controller('ComparisonDetailController', ['$scope', '$http', '$routeParams', '$timeout', '$location', '$filter', 'ngTableParams',
    function ($scope, $http, $routeParams, $timeout, $location, $filter, ngTableParams) {
        $scope.loading = true;
        $scope.notfound = false;
        $scope.found = true;

        $scope.comparison = {};
        $scope.location = $location;

        $http.get('/api/admin/featureFlags/socialSharing').
          success(function (data) {
              if (data == 'true')
                $scope.social_sharing = true;
              else
                $scope.social_sharing = false;
          });

        var retrieveComparisons = function () {
            $http.get('/api/strava/comparisons/' + $routeParams.comparisonId).
                success(function (data) {
                    $scope.tableParams = new ngTableParams({
                        page: 1,
                        count: 10,
                        sorting: {}
                    }, {
                        total: 0,
                        getData: function($defer, params) {
                            var orderedData = params.sorting() ?
                                $filter('orderBy')(data.comparisons, params.orderBy()) : data.comparisons;
                            params.total(data.comparisons.length);
                            $defer.resolve(orderedData.slice((params.page() - 1) * params.count(), params.page() * params.count()));
                        }
                    });

                    var sum = 0;
                    var win = 0;
                    var loss = 0;
                    var tied = 0;
                    var ddata = [];
                    var cdata = [];

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

                        data.comparisons[i].per_diff = diff/c.effort.moving_time;

                        ddata.push({"x": c.effort.distance, "y": diff, "size": diff/c.effort.moving_time, "text": c.segment.name});
                        cdata.push({"x": c.segment.average_grade, "y": diff, "size": diff/c.effort.moving_time, "text": c.segment.name});
                    }

                    $scope.distanceScatter = [
                        {
                            "key": "Distance",
                            "values": ddata
                        }
                    ];

                    $scope.climbScatter = [
                        {
                            "key": "Grade",
                            "values": cdata
                        }
                    ];

                    $scope.$on('elementMouseover.tooltip.directive', function(angularEvent, event){
                        angularEvent.targetScope.$parent.hovername = event.point.text;
                        angularEvent.targetScope.$parent.hoverdiff = event.point.size;
                        angularEvent.targetScope.$parent.$digest();
                    });

                    $scope.$on('elementMouseout.tooltip.directive', function(angularEvent, event){
                        angularEvent.targetScope.$parent.hovername = undefined;
                        angularEvent.targetScope.$parent.hoverdiff = undefined;
                            angularEvent.targetScope.$parent.$digest();
                    });

                    $scope.scolorFunction = function() {
                        return function(d, i) {
                            return '#FC4C02';
                        };
                    }

                    $scope.yAxisTickFormatFunction = function(x) {
                        return function(d) {
                            return d.toFixed(0) + 's';
                        }
                    }

                    $scope.xAxisTickFormatFunction = function(x) {
                        return function(d) {
                            return format_distance(d, mp);
                        }
                    }

                    $scope.xAxisTickFormatGradeFunction = function(x) {
                        return function(d) {
                            return d.toFixed(1) + '%';
                        }
                    }

                    $scope.comparison = data;
                    $scope.weighted_average_distance = get_distance_weighted_average(data.comparisons);
                    $scope.weighted_average_climb = get_climbing_weighted_average(data.comparisons);
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

                    $scope.found = true;
                    $scope.notfound = false;
                    $scope.loading = false;
                }).error(function (error) {
                    console.log('error loading comparison: ' + JSON.stringify(error));
                    $scope.found = false;
                    $scope.notfound = true;
                    $scope.loading = false;
                });
        }

        if (mp == undefined) {
            $http.get('/api/strava/athlete').
                success(function (data) {
                    mp = data.measurement_preference;
                    $scope.measurement_preference = mp;
                    retrieveComparisons();
                });
        } else {
            $scope.measurement_preference = mp;
            retrieveComparisons();
        }

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
    image.src = '/assets/no_image_small.png';
}

function weight(meters) {
    if (meters <= 804.672) // 1/2 mile
        return 1;
    else if (meters <= 1609.34) // 1 mile
        return 2;
    else if (meters <= 2414.02) // 1.5 miles
        return 3;
    else if (meters <= 3218.69) // 2 miles
        return 4;
    else
        return 5;
}
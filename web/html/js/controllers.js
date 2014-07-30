
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
           console.log('event received: ' + JSON.stringify(data));
            $scope.comparisons.unshift(data);
        });

        $scope.$on('errorlaunch', function(event, error) {
           console.log('error received: ', JSON.stringify(error));
           console.log('error received: ', JSON.stringify(error));
        });
    }]);

appControllers.controller('NewComparisonController', ['$scope', '$http',
    function($scope, $http) {
        $scope.days_ago = 1;

        $scope.openLaunch = function() {
          $scope.showDialog = true;
        };

        $scope.closeLaunch = function() {
            $scope.showDialog = false;
        }

        $scope.submitLaunch = function() {
            console.log('we should launch something!');
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
    }]);

appControllers.controller('ComparisonDetailController', ['$scope', '$http', '$routeParams', '$timeout',
    function ($scope, $http, $routeParams, $timeout) {
        $scope.comparison = {};

        var retrieveComparisons = function () {
            $http.get('/api/strava/comparisons/' + $routeParams.comparisonId).
                success(function (data) {
                    $scope.comparison = data;

                    if (data.state == 'Running') {
                        $timeout(retrieveComparisons, 1000)
                    }
                });
        }

        // initial retrieval
        retrieveComparisons();
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
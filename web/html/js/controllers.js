
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
    }]);

appControllers.controller('ComparisonDetailController', ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {
        $scope.comparison = {};

        $http.get('/api/strava/comparisons/' + $routeParams.comparisonId).
            success(function (data) {
                $scope.comparison = data;
            });
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
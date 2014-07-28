
var appControllers = angular.module('appControllers', ['ipCookie']);

appControllers.controller('MainController', ['$scope', '$routeParams', '$http', 'ipCookie',
	function($scope, $routeParams, $http, ipCookie) {
		
		$scope.sessionId = ipCookie('stravaSocialSessionId');
		
		if ($scope.sessionId) {
			$http.get('/api/strava/authorizations/' + $scope.sessionId + '/isvalid').
				success(function(data) {
					$scope.sessionIsValid = data.is_valid;

					$http.get('/api/strava/athletes/' + data.athlete_id).
						success(function(data) {
							$scope.athlete = data;
						});
				});
		}
		
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
					$scope.sessionIsValid = null;
					$scope.athlete = null;
					ipCookie.remove('stravaSocialSessionId');
				});
		};	
	}
]);
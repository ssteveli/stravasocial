var app = angular.module('app', ['stravaReturnControllers', 'ipCookie']);

app.config(['$locationProvider', function ($locationProvider) {
	$locationProvider.html5Mode(true);
}]);

var stravaReturnControllers = angular.module('stravaReturnControllers', []);
stravaReturnControllers.controller('StravaReturnController', ['$scope', '$location', '$http', 'ipCookie',
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

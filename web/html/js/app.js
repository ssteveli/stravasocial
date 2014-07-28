var app = angular.module('app', [
	'ngRoute',
    'ngTable',
	'ipCookie',
	'appControllers'
]);

app.config(['$routeProvider', '$locationProvider',
	function($routeProvider, $locationProvider) {
		$locationProvider.html5Mode(true);

		$routeProvider.
			when('/', {
				templateUrl: 'home.html',
				controller: 'MainController'
			}).
            when('/comparisons', {
                templateUrl: 'comparisons.html',
                controller: 'ComparisonController'
            });
	}
]);

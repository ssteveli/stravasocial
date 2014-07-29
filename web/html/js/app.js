var app = angular.module('app', [
	'ngRoute',
    'ngTable',
	'ipCookie',
	'appControllers',
    'myFilters'
]);

app.config(['$routeProvider', '$locationProvider',
	function($routeProvider, $locationProvider) {
		$locationProvider.html5Mode(true);

		$routeProvider.
			when('/', {
				templateUrl: 'home.html',
				controller: 'MainController'
			}).
            when('/about', {
                templateUrl: 'about.html',
                controller: 'MainController'
            }).
            when('/comparisons', {
                templateUrl: 'comparisons.html',
                controller: 'ComparisonController'
            });
	}
]);

angular.module('myFilters', []).filter('timeago', function() {
    return function(input) {
        console.log('here we go!');
        return $.timeago(new Date(input));
    }
});
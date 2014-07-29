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
            }).
            when('/comparisons/:comparisonId', {
                templateUrl: '/comparison-detail.html',
                controller: 'ComparisonDetailController'
            });
	}
]);

angular.module('myFilters', []).filter('timeago', function() {
    return function(input) {
        return $.timeago(new Date(input));
    }
}).filter('feet', function() {
    return function(input) {
        var i = parseFloat(input);
        return (i * 0.000621371).toFixed(2) + 'mi';
    }
}).filter('seconds', function() {
   return function(input) {
       var sec_num = parseInt(input, 10); // don't forget the second param
       var hours   = Math.floor(sec_num / 3600);
       var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
       var seconds = sec_num - (hours * 3600) - (minutes * 60);

       if (hours   < 10) {hours   = "0"+hours;}
       if (minutes < 10) {minutes = "0"+minutes;}
       if (seconds < 10) {seconds = "0"+seconds;}
       var time    = hours+':'+minutes+':'+seconds;
       return time;
   }
});
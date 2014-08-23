var app = angular.module('app', [
	'ngRoute',
    'ngResource',
    'ngTable',
	'appControllers',
    'myFilters',
    'nvd3ChartDirectives',
    'ui.bootstrap',
    'LocalStorageModule'
]);

app.run(['$rootScope', '$location', '$window', function ($rootScope, $location, $window) {
    $rootScope.$on('$routeChangeSuccess', function() {
        if (!$window.ga) {
            console.log('skipping google pageview, no ga available');
            return;
        }

        $window.ga('send', 'pageview', {page: $location.path()});
    });
}]);

app.factory('AuthenticationService', function($window, localStorageService) {
    var auth = {
        isLogged: localStorageService.get('token') != undefined ? true : false
    };

    return auth;
});

app.factory('Error', function() {
    return {message:undefined};
});

app.factory('Athlete', function($http, $q) {
    return {
        getAthlete: function() {
            var d = $q.defer();
            $http.get('/api/strava/athlete')
                .success(function (data) {
                    d.resolve(data);
                })
                .error(function (msg, code) {
                    d.reject(msg);
                    console.log('failed to retrieve athlete: ' + JSON.stringify(msg));
                });

            return d.promise;
        },
        getPlan: function() {
            var d = $q.defer();
            $http.get('/api/strava/athlete/plan')
                .success(function (data) {
                    d.resolve(data);
                })
                .error(function (msg, code) {
                    d.reject(msg);
                    console.log('failed to retrieve the athlete plan: ' + JSON.stringify(msg));
                });
            return d.promise;
        }
    };
});

app.factory('authInterceptor', function($rootScope, $q, $window, localStorageService) {
   return {
       request: function(config) {
           config.headers = config.headers || {};
           if (localStorageService.get('token')) {
               config.headers.Authorization = 'Bearer ' + localStorageService.get('token');
           }

           return config;
       },
       response: function(response) {
           if (response.status == 401) {
               console.log('user is not authenticated, now what?');
           }

           return response || $q.when(response);
       }
   };
});

app.config(function ($httpProvider) {
    $httpProvider.interceptors.push('authInterceptor');
});

app.config(['$routeProvider', '$locationProvider',
	function($routeProvider, $locationProvider) {
		$locationProvider.html5Mode(true);

		$routeProvider.
			when('/', {
				templateUrl: '/home.html',
				controller: 'MainController'
			}).
            when('/home', {
                templateUrl: '/home.html',
                controller: 'MainController'
            }).
            when('/stravareturn', {
                templateUrl: '/stravareturn.html',
                controller: 'StravaReturnController'
            }).
            when('/about', {
                templateUrl: '/about.html',
                controller: 'MainController'
            }).
            when('/comparisons', {
                templateUrl: '/comparisons.html',
                controller: 'ComparisonController'
            }).
            when('/comparisons/:comparisonId', {
                templateUrl: '/comparison-detail.html',
                controller: 'ComparisonDetailController'
            })
            .when('/error', {
                templateUrl: '/error.html',
                controller: 'ErrorController'
            });
	}
]);

app.directive('loadingContainer', function () {
    return {
        restrict: 'A',
        scope: false,
        link: function(scope, element, attrs) {
            var loadingLayer = angular.element('<div class="loading"></div>');
            element.append(loadingLayer);
            element.addClass('loading-container');
            scope.$watch(attrs.loadingContainer, function(value) {
                loadingLayer.toggleClass('ng-hide', !value);
            });
        }
    };
});

// borrowed from http://stackoverflow.com/questions/15399958/closing-twitter-bootstrap-modal-from-angular-controller
app.directive("modalShow", function () {
    return {
        restrict: "A",
        scope: {
            modalVisible: "="
        },
        link: function (scope, element, attrs) {

            //Hide or show the modal
            scope.showModal = function (visible) {
                if (visible)
                {
                    element.modal("show");
                }
                else
                {
                    element.modal("hide");
                }
            }

            //Check to see if the modal-visible attribute exists
            if (!attrs.modalVisible)
            {

                //The attribute isn't defined, show the modal by default
                scope.showModal(true);

            }
            else
            {
                //Watch for changes to the modal-visible attribute
                scope.$watch("modalVisible", function (newValue, oldValue) {
                    scope.showModal(newValue);
                });

                //Update the visible value when the dialog is closed through UI actions (Ok, cancel, etc.)
                element.bind("hide.bs.modal", function () {
                    scope.modalVisible = false;
                    if (!scope.$$phase && !scope.$root.$$phase)
                        scope.$apply();
                });

            }

        }
    };

});

angular.module('myFilters', []).filter('timeago', function() {
    return function(input) {
        return $.timeago(new Date(input));
    }
}).filter('feet', function() {
    return function(input, pref) {
        return format_distance(input, pref);
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
}).filter('secondstotime', function() {
    return function (input) {
        return format_seconds(input);
    }
});

function format_distance(input, pref) {
    var i = parseFloat(input);

    if (pref == 'feet') {
        return (i * 0.000621371).toFixed(2) + ' mi';
    } else {
        return (i * 0.001).toFixed(2) + ' km';
    }
}

function format_seconds(input) {
    var i = Math.abs(input);

    var hours = Math.floor(i / (60*60));
    var divisor_for_minutes = i % (60*60);
    var minutes = Math.floor(divisor_for_minutes / 60);
    var divisor_for_seconds = divisor_for_minutes % 60;
    var seconds = Math.floor(divisor_for_seconds);

    var s = '';

    if (hours > 0) {
        s += hours + ' hr ';
    }

    if (minutes > 0) {
        s += minutes + ' min ';
    }

    if (seconds > 0) {
        s += seconds + ' sec' + ((seconds > 1) ? 's' : '');
    }

    return s;
}
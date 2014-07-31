var app = angular.module('app', [
	'ngRoute',
    'ngTable',
	'ipCookie',
	'appControllers',
    'myFilters',
    'nvd3ChartDirectives'
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
/**
 * Created by ssteveli on 8/12/14.
 */

function get_weighted_average(c, weight) {
    var wc = 0;
    var wt = 0;

    for (var i=0; i<c.length; i++) {
        var diff = (c[i].compared_to_effort.moving_time - c[i].effort.moving_time);
        var w = weight(c[i]);
        wc += w;
        wt += (((diff / c[i].effort.moving_time)) * w);
    }

    return (wt/wc)*100;
}

function get_distance_weighted_average(c) {
    return get_weighted_average(c, distanceWeight);
}

function get_climbing_weighted_average(c) {
    return get_weighted_average(c, gradeWeight);
}

function distanceWeight(c) {
    var meters = c.effort.distance;
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

function gradeWeight(c) {
    if (c.segment.average_grade) {
        var grade = c.segment.average_grade;
        return grade * 2;
    } else
        return 0;
}

/**
 * Created by ssteveli on 8/12/14.
 */

function get_weighted_average(c) {
    var wc = 0;
    var wt = 0;

    for (var i=0; i<c.length; i++) {
        var diff = (c[i].compared_to_effort.moving_time - c[i].effort.moving_time);
        var w = weight(c[i].effort.distance);
        wc += w;
        wt += (((diff / c[i].effort.moving_time) * 100) * w);
    }

    return wt/wc;
}

function weight(meters) {
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

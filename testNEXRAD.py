# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 9 Apr 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from nightshift import radar, common


if __name__ == "__main__":
    inloc = "./inputs/radar/"
    outloc = "./outputs/radar/pngs/"
    cfiles = "./nightshift/resources/cb_2018_us_county_5m/"

    # in degrees
    mapcenter = [-111.4223, 34.7443]
    filterRadius = 7.

    cmap = radar.plot.getCMap()
    rclasses = ["Interstate", "Federal"]

    print("Reading road data...")
    roads = common.maps.parseRoads(rclasses,
                                   center=mapcenter, centerRad=filterRadius)
    for rkey in rclasses:
        print("%s: %d found within %d degrees of center" % (rkey,
                                                            len(roads[rkey]),
                                                            filterRadius))

    counties = common.maps.parseCounties(cfiles + "cb_2018_us_county_5m.shp",
                                         center=mapcenter,
                                         centerRad=filterRadius)
    print("%d counties found within %d degrees of center" % (len(counties),
                                                             filterRadius))
    radar.plot.makePlots(inloc, outloc, mapcenter, cmap=cmap,
                         roads=roads, counties=counties,
                         forceRegen=True)

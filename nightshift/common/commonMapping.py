# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 22 May 2019
#
#  @author: rhamilton

"""
"""

from __future__ import division, print_function, absolute_import

import numpy as np

import cartopy.crs as ccrs
import cartopy.feature as cfeat
from cartopy.feature import sgeom
import cartopy.io.shapereader as cshape


def set_plot_extent(clat, clon, radius=200., fudge=0.053):
    # Output grid centered on clat, clon
    # latWid = 3.5
    # lonWid = 3.5
    # lonMin = clon - lonWid
    # lonMax = clon + lonWid
    # latMin = clat - latWid
    # latMax = clat + latWid

    # Handpicked favorites; generates all of AZ centered on the DCT
    # latWid = 3.5
    # lonWid = 3.5
    # lonMin = clon - lonWid
    # lonMax = clon + lonWid - 1.0
    # latMin = clat - latWid
    # latMax = clat + latWid - 0.75

    # Zoomed in portion around the DCT, showing an approximate radius
    #   of 'desiredRadius' statute miles.
    # To do this right it's easier to think in terms of nautical miles;
    #   See https://github.com/LowellObservatory/Camelot/issues/5 for the math.

    # In *statute miles* since they're easier to measure (from Google Maps)
    desiredRadius = radius

    # Now it's in nautical miles so we just continue
    dRnm = desiredRadius/1.1507794
    latWid = dRnm/60.
    lonWid = dRnm/(np.cos(np.deg2rad(clat))*60.)

    # Small fudge factor to make the aspect a little closer to 1:1
    latWid += fudge

    print(latWid, lonWid)

    lonMin = clon - lonWid
    lonMax = clon + lonWid
    latMin = clat - latWid
    latMax = clat + latWid

    return latMin, latMax, lonMin, lonMax


def add_map_features(ax, counties=None, roads=None):
    """
    """
    ax.add_feature(cfeat.COASTLINE.with_scale('10m'))
    ax.add_feature(cfeat.BORDERS.with_scale('10m'))

    # Slightly transparent rivers
    ax.add_feature(cfeat.RIVERS.with_scale('10m'),
                   alpha=0.75, edgecolor='aqua')

    # Dotted lines for state borders
    ax.add_feature(cfeat.STATES.with_scale('10m'),
                   linestyle=":", edgecolor='black')

    if counties is not None:
        countfeat = cfeat.ShapelyFeature(counties, ccrs.PlateCarree())
        ax.add_feature(countfeat, facecolor='none',
                       edgecolor='#ff0092', alpha=0.25)

    if roads is not None:
        # Reminder that roads is a dict with keys:
        #  interstates, fedroads, stateroads, otherroads
        for rtype in roads:
            good = True
            if rtype == "Interstate":
                rcolor = 'gold'
                ralpha = 0.55
            elif rtype == "Federal":
                rcolor = 'gold'
                ralpha = 0.55
            elif rtype == 'State':
                rcolor = 'LightSkyBlue'
                ralpha = 0.55
            elif rtype == "Other":
                rcolor = 'LightSkyBlue'
                ralpha = 0.45
            else:
                good = False

            # Only plot the ones specifed above; if it doesn't fit one of
            #   those categories then skip it completely because something
            #   is wrong or changed.
            if good is True:
                sfeat = cfeat.ShapelyFeature(roads[rtype], ccrs.PlateCarree())
                ax.add_feature(sfeat, facecolor='none',
                               edgecolor=rcolor, alpha=ralpha)

    return ax


def checkGeomDistance(centerPt, rec, centerRad):
    """
    """
    # Since the geometry coordinates are in lon/lat, the
    #   corresponding 'dist' will be too; therefore we filter
    #   based on a radius of N degrees from the center
    # centerRad == 7 covers a big area so we'll roll with that
    dist = rec.geometry.distance(centerPt)
    if dist <= centerRad:
        store = True
    else:
        store = False

    return store


def parseCounties(shpfile, center=None, centerRad=7.):
    """
    """
    counties = cshape.Reader(shpfile)

    # If we have coordinates of the center of the map, enable
    #   spatial filtering of the roads to within some radius of center
    spatialFilter = False
    if center is not None:
        spatialFilter = True
        mapCenterPt = sgeom.Point(center[0], center[1])

    clist = []
    # A dict is far easier to interact with so make one
    for rec in counties.records():
        if spatialFilter is True:
            store = checkGeomDistance(mapCenterPt, rec, centerRad)
        else:
            store = True

        if store is True:
            clist.append(rec.geometry)

    return clist


def parseRoads(rclasses, center=None, centerRad=7.):
    """
    See https://www.naturalearthdata.com/downloads/10m-cultural-vectors/roads/
    for field information; below is just a quick summary.

    CLASS:
        Interstate (Interstates and Quebec Autoroutes)
        Federal (US Highways, Mexican Federal Highways, Trans-Canada Highways)
        State (US State, Mexican State, and Canadian Provincial Highways)
        Other (any other road class)
        Closed (road is closed to public)
        U/C (road is under construction)
    TYPE:
        Tollway
        Freeway
        Primary
        Secondary
        Other Paved
        Unpaved
        Winter (ice road, open winter only)
        Trail
        Ferry
    """
    rds = cshape.natural_earth(resolution='10m',
                               category='cultural',
                               name='roads_north_america')

    rdsrec = cshape.Reader(rds)

    # If we have coordinates of the center of the map, spatially filter
    #   the roads down to just those w/in 500 miles of the center
    spatialFilter = False
    if center is not None:
        spatialFilter = True
        mapCenterPt = sgeom.Point(center[0], center[1])

    rdict = {}
    # A dict is far easier to interact with so make one
    for rec in rdsrec.records():
        for key in rclasses:
            if rec.attributes['class'] == key:
                if spatialFilter is True:
                    store = checkGeomDistance(mapCenterPt, rec, centerRad)
                else:
                    store = True

                if store is True:
                    try:
                        rdict[key].append(rec.geometry)
                    except KeyError:
                        # This means the key hasn't been created yet so make it
                        #   and then fill it with the value.
                        #   It should then work fine the next time
                        rdict.update({key: [rec.geometry]})

    return rdict


def add_AZObs(ax):
    """
    Hardcoded this for now, with a Lowell/Mars Hill getting a "*" marker.

    Would be easy to pass in a dict of locations and marker/color info too
    and just loop through that, but since I only have 5 now it's no big deal.
    """
    # Lowell
    ax.plot(-111.664444, 35.202778, marker='*', color='red',
            markersize=8, alpha=0.95, transform=ccrs.Geodetic())

    # DCT
    ax.plot(-111.4223, 34.7443, marker='o', color='red', markersize=6,
            alpha=0.95, transform=ccrs.Geodetic())

    # Anderson Mesa
    ax.plot(-111.535833, 35.096944, marker='o', color='red',
            markersize=6, alpha=0.95, transform=ccrs.Geodetic())

    # KPNO
    ax.plot(-111.5967, 31.9583, marker='o', color='purple',
            markersize=5, alpha=0.95, transform=ccrs.Geodetic())

    # LBT
    ax.plot(-109.889064, 32.701308, marker='o', color='purple',
            markersize=5, alpha=0.95, transform=ccrs.Geodetic())

    # MMT
    ax.plot(-110.885, 31.6883, marker='o', color='purple',
            markersize=5, alpha=0.95, transform=ccrs.Geodetic())

    return ax

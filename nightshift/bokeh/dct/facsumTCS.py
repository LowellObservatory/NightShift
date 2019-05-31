# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 7 May 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import datetime as dt
from collections import OrderedDict

import numpy as np

from bokeh.plotting import ColumnDataSource

from ..plotting import helpers
from ..plotting import tables as tabs


def dataGatherer(moduleKey, mods, qdata):
    """
    Instrument/plot/query specific contortions needed to make the
    bulk of the plot code generic and abstract.  I feel ok
    hardcoding stuff in here at least, since this will always be namespace
    protected and unambigious (e.g. instrumentTelem.dataGatherer).
    """
    m = mods[moduleKey]
    print("Fetching data for %s" % (m.title))

    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    # Get the keys that define the input dataset.
    r = pdata['q_tcssv']

    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # Now the tedious bit - reassemble the shredded parameters like RA/Dec/etc.
    #   Whomever designed the TCS XML...know that I'm not a fan of your work.

    # CURRENT coords
    cRA_h = helpers.getLast(r, "cRA_h", compTime=now, nullVal=-1)
    cRA_m = helpers.getLast(r, "cRA_m", compTime=now, nullVal=-1)
    cRA_s = helpers.getLast(r, "cRA_s", compTime=now, nullVal=-1)

    cDec_d = helpers.getLast(r, "cDec_d", compTime=now, nullVal=-1)
    cDec_m = helpers.getLast(r, "cDec_m", compTime=now, nullVal=-1)
    cDec_s = helpers.getLast(r, "cDec_s", compTime=now, nullVal=-1)

    cEquinoxPrefix = helpers.getLast(r, "cEqP",
                                     label="Current Equinox Prefix",
                                     compTime=now, nullVal=-1)
    cEquinoxYear = helpers.getLast(r, "cEqY",
                                   label="Current Equinox Year",
                                   compTime=now, nullVal=-1)
    cFrame = helpers.getLast(r, "cFrame", label="Current Frame",
                             compTime=now, nullVal=-1)

    cAz_d = helpers.getLast(r, "cAz_d", compTime=now, nullVal=-1)
    cAz_m = helpers.getLast(r, "cAz_m", compTime=now, nullVal=-1)
    cAz_s = helpers.getLast(r, "cAz_s", compTime=now, nullVal=-1)

    cEl_d = helpers.getLast(r, "cEl_d", compTime=now, nullVal=-1)
    cEl_m = helpers.getLast(r, "cEl_m", compTime=now, nullVal=-1)
    cEl_s = helpers.getLast(r, "cEl_s", compTime=now, nullVal=-1)

    # DEMAND coords
    dRA_h = helpers.getLast(r, "dRA_h", compTime=now, nullVal=-1)
    dRA_m = helpers.getLast(r, "dRA_m", compTime=now, nullVal=-1)
    dRA_s = helpers.getLast(r, "dRA_s", compTime=now, nullVal=-1)

    dDec_d = helpers.getLast(r, "dDec_d", compTime=now, nullVal=-1)
    dDec_m = helpers.getLast(r, "dDec_m", compTime=now, nullVal=-1)
    dDec_s = helpers.getLast(r, "dDec_s", compTime=now, nullVal=-1)

    dEquinoxPrefix = helpers.getLast(r, "dEqP",
                                     label="Demand Equinox Prefix",
                                     compTime=now, nullVal=-1)
    dEquinoxYear = helpers.getLast(r, "dEqY",
                                   label="Demand Equinox Year",
                                   compTime=now, nullVal=-1)
    dFrame = helpers.getLast(r, "dFrame", label="Demand Frame",
                             compTime=now, nullVal=-1)

    # HA
    cHA_h = helpers.getLast(r, "cHA_h", compTime=now, nullVal=-1)
    cHA_m = helpers.getLast(r, "cHA_m", compTime=now, nullVal=-1)
    cHA_s = helpers.getLast(r, "cHA_s", compTime=now, nullVal=-1)

    # LST
    LST_h = helpers.getLast(r, "LST_h", compTime=now, nullVal=-1)
    LST_m = helpers.getLast(r, "LST_m", compTime=now, nullVal=-1)
    LST_s = helpers.getLast(r, "LST_s", compTime=now, nullVal=-1)

    # Put it all together again
    cRA = helpers.deshred([cRA_h, cRA_m, cRA_s],
                          delim=":", name="Current RA")
    cDec = helpers.deshred([cDec_d, cDec_m, cDec_s],
                           delim=":", name="Current Dec")
    cRef = helpers.deshred([cEquinoxPrefix, cEquinoxYear],
                           delim="", name="Current Reference Frame")
    cFin = helpers.deshred([cRA, cDec, cRef, cFrame],
                           delim=" ", name="Current Sky Coordinates")

    cAz = helpers.deshred([cAz_d, cAz_m, cAz_s],
                          delim=":", name="Current Azimuth")
    cEl = helpers.deshred([cEl_d, cEl_m, cEl_s],
                          delim=":", name="Current Elevation")
    cAzEl = helpers.deshred([cAz, cEl],
                            delim=" / ", name="Current Az/El")

    dRA = helpers.deshred([dRA_h, dRA_m, dRA_s],
                          delim=":", name="Demand RA")
    dDec = helpers.deshred([dDec_d, dDec_m, dDec_s],
                           delim=":", name="Demand Dec")
    dRef = helpers.deshred([dEquinoxPrefix, dEquinoxYear],
                           delim="", name="Current Reference Frame")
    dFin = helpers.deshred([dRA, dDec, dRef, dFrame],
                           delim=" ", name="Demand Sky Coordinates")

    cHA = helpers.deshred([cHA_h, cHA_m, cHA_s], delim=":", name="Current HA")

    lst = helpers.deshred([LST_h, LST_m, LST_s], delim=":", name="TCS LST")

    airmass = helpers.getLast(r, "Airmass", compTime=now, fstr="%.2f")
    targname = helpers.getLast(r, "TargetName", compTime=now)
    guidemode = helpers.getLast(r, "GuideMode", compTime=now)
    sundist = helpers.getLast(r, "SunDistance", compTime=now, fstr="%.2f")
    moondist = helpers.getLast(r, "MoonDistance", compTime=now, fstr="%.2f")

    # Now snag our pyephem ephemeris information
    e = qdata['ephemera']
    sunrise = helpers.getLast(e, "sunrise", label='Sunrise', compTime=now)
    sunset = helpers.getLast(e, "sunset", label='Sunset', compTime=now)

    # nsunrise = helpers.getLast(e.nextsunrise, label='Next Sunrise',
    #                          compTime=now)
    # nsunset = helpers.getLast(e.nextsunset, label='Next Sunset',
    #                         compTime=now)

    sunalt = helpers.getLast(e, "sun_dms", label='Sun Altitude',
                             compTime=now, fstr="%.2f")
    moonalt = helpers.getLast(e, "moon_dms", label='Moon Altitude',
                              compTime=now, fstr="%.2f")
    moonphase = helpers.getLast(e, "moonphase", scaleFactor=100.,
                                label='Moon Phase',
                                compTime=now, fstr="%.2f")

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [sunset, sunrise,
                targname, lst,
                cHA,
                cAzEl,
                cFin,
                dFin,
                # RA, dRA,
                # cDec, dDec,
                # cFrame, dFrame,
                airmass, guidemode,
                sundist, moondist,
                sunalt, moonalt, moonphase]

    values = []
    labels = []
    tooold = []
    for each in tableDat:
        if each.label.lower().find("rise") != -1 or\
           each.label.lower().find("set") != -1:
            values.append(each.value.strftime("%Y-%m-%d %H:%M:%S %Z"))
        else:
            values.append(each.value)

        labels.append(each.label)
        tooold.append(each.tooOld)

    mds = dict(labels=labels, values=values, ageStatement=tooold)
    cds = ColumnDataSource(mds)

    return cds


def makeFacSum(doc):
    """
    This is called every time someone visits a pre-defined endpoint;
    see the apps dict in the main calling code for what that actualls is.
    """
    # Grab our stashed information from the template
    plotState = doc.template.globals['plotState']

    mods = plotState.modules
    qdata = plotState.data
    theme = plotState.theme

    modKey = 'facsum_tcs'

    #
    # AWWWWW YEAAAAAAHHHH THIS IS COMPLETELY GENERIC NOW
    #
    # Use this to consistently filter/gather the data based on some
    #   specific tags/reorganizing
    cds = dataGatherer(modKey, mods, qdata)

    dtab, nRows = tabs.setupTable(cds)

    dtab.width = 390
    dtab.height = 510
    dtab.margin = 0
    dtab.header_row = False

    doc.theme = theme
    doc.title = mods[modKey].title
    doc.add_root(dtab)

    def grabNew():
        print("Checking for new data!")

        # WHYYYYYYY do I have to do this now? I feel like I didn't like
        #   5 minutes ago but now cds isn't inherited, but m and r are. WTF!
        cds = doc.roots[0].source

        # Check our stash
        qdata = doc.template.globals['plotState'].data
        timeUpdate = doc.template.globals['plotState'].timestamp
        tdiff = (dt.datetime.utcnow() - timeUpdate).total_seconds()
        print("Data were queried %f seconds ago (%s)" % (tdiff, timeUpdate))

        # Let's just be dumb and replace everything all at once
        ncds = dataGatherer(modKey, mods, qdata)
        cds.stream(ncds.data, rollover=nRows)

    print("Set doc periodic callback")
    doc.add_periodic_callback(grabNew, 5000)

    return doc

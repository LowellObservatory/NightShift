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

import numpy as np

from bokeh.plotting import ColumnDataSource

from . import ldtWeather
from ..plotting import helpers
from ..plotting import tables as tabs


def filterAndJudge(r):
    """
    Given a dataframe, find the last entries and judge them. Then turn
    the final result into a ColumnDataSource that can be put into a table.
    """
    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # These are from other data sources, so get their values too
    temp = helpers.getLast(r, "AirTemp",
                           compTime=now, nullVal=None, fstr="%.1f")
    dewp = helpers.getLast(r, "DewPoint",
                           compTime=now, nullVal=None, fstr="%.1f")
    moun = helpers.getLast(r, "MountTemp",
                           compTime=now, nullVal=None, fstr="%.1f")
    humi = helpers.getLast(r, "Humidity",
                           compTime=now, nullVal=None, fstr="%.1f")

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [temp, dewp, moun, humi]

    values = []
    labels = []
    tooold = []
    for each in tableDat:
        values.append(each.value)
        labels.append(each.label)
        tooold.append(each.tooOld)

    mds = dict(labels=labels, values=values, ageStatement=tooold)
    cds = ColumnDataSource(mds)

    return cds


def makeTable(doc):
    """
    This is called every time someone visits a pre-defined endpoint;
    see the apps dict in the main calling code for what that actualls is.
    """
    # Grab our stashed information from the template
    plotState = doc.template.globals['plotState']

    mods = plotState.modules
    qdata = plotState.data
    theme = plotState.theme

    moduleKey = 'weather_TempHumi'
    m = mods[moduleKey]

    print("Serving table %s" % (m.title))

    # Reuse our old function that arranges the data, then we'll just
    #   downselect to the very last row
    r = ldtWeather.dataGatherer(m, qdata)
    cds = filterAndJudge(r)

    dtab, nRows = tabs.setupTable(cds)

    dtab.width = 250
    dtab.height = 125
    dtab.margin = 0
    dtab.header_row = False

    doc.theme = theme
    doc.title = m.title
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
        nr = ldtWeather.dataGatherer(m, qdata)
        ncds = filterAndJudge(nr)

        cds.stream(ncds.data, rollover=nRows)

    print("Set doc periodic callback")
    doc.add_periodic_callback(grabNew, 5000)

    return doc

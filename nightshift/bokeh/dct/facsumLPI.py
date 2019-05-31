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


def dataGatherer(m, qdata):
    """
    Instrument/plot/query specific contortions needed to make the
    bulk of the plot code generic and abstract.  I feel ok
    hardcoding stuff in here at least, since this will always be namespace
    protected and unambigious (e.g. instrumentTelem.dataGatherer).
    """
    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    r = pdata['q_tcssv']
    r2 = pdata['q_tcslois']
    r3 = pdata['q_cubeinstcover']
    r4 = pdata['q_cubefolds']
    r5 = pdata['q_aossv']

    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # These are from other data sources, so get their values too
    domeshut = helpers.getLast(r2, "DomeShutter", compTime=now)
    mirrorcov = helpers.getLast(r, "MirrorCover", compTime=now)

    # We use the nullVal parameter for these so we can catch the
    #   .likelyInvalid parameters in the final table data collection since
    #   they have special logic a little down below
    instcover = helpers.getLast(r3, "InstCover", compTime=now, nullVal=-1)

    portT = helpers.getLast(r4, 'PortThru', compTime=now, nullVal=-1)
    portA = helpers.getLast(r4, 'PortA', compTime=now, nullVal=-1)
    portB = helpers.getLast(r4, 'PortB', compTime=now, nullVal=-1)
    portC = helpers.getLast(r4, 'PortC', compTime=now, nullVal=-1)
    portD = helpers.getLast(r4, 'PortD', compTime=now, nullVal=-1)

    m2piston = helpers.getLast(r5, 'M2PistonDemand',
                               label="Demand M2 Piston",
                               compTime=now, scaleFactor=1e6, fstr="%.3f")
    totfocus = helpers.getLast(r5, 'totalFocusOffset',
                               label="Total Focus Offset",
                               compTime=now, scaleFactor=1e6, fstr="%.3f")

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [domeshut, mirrorcov, instcover, m2piston, totfocus,
                portT, portA, portB, portC, portD]

    values = []
    labels = []
    tooold = []
    for each in tableDat:
        if each.label == "InstCover":
            # Special conversion to text for this one
            if each.value == 0:
                values.append("Closed")
            elif each.value == -1:
                values.append(helpers.funnyValues())
            else:
                values.append("Open")
            labels.append(each.label)
        elif each.label.startswith("Port"):
            if each.value == 0:
                values.append("Inactive")
            elif each.value == -1:
                values.append(helpers.funnyValues())
            else:
                values.append("Active")
            labels.append(each.label)
        else:
            values.append(each.value)
            labels.append(each.label)

        # Rather than put this in each elif, I'll just do it here.
        #   Add in our age comparison column, for color/styling later
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

    moduleKey = 'facsum_lpi'
    m = mods[moduleKey]

    print("Serving %s" % (m.title))

    # Use this to consistently filter/gather the data based on some
    #   specific tags/reorganizing
    cds = dataGatherer(m, qdata)

    dtab, nRows = tabs.setupTable(cds)

    dtab.width = 390
    dtab.height = 290
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
        ncds = dataGatherer(m, qdata)
        cds.stream(ncds.data, rollover=nRows)

    print("Set doc periodic callback")
    doc.add_periodic_callback(grabNew, 5000)

    return doc

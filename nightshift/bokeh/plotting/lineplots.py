# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 31 May 2019
#
#  @author: rhamilton

"""Collection of helper routines used when making Bokeh line plots.

Further description.
"""

from __future__ import division, print_function, absolute_import

import numpy as np
import pandas as pd

from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import Span, DataRange1d, LinearAxis
from bokeh.models import Legend, LegendItem, HoverTool

from . import helpers


def commonPlot(r, ldict, y1lim, dset, height=None, width=None, y2=None):
    """
    """
    tools = "pan, wheel_zoom, box_zoom, crosshair, reset, save"

    title = ldict['title']
    xlabel = ldict['xlabel']
    y1label = ldict['y1label']

    p = figure(title=title, x_axis_type='datetime',
               x_axis_label=xlabel, y_axis_label=y1label,
               tools=tools, output_backend="webgl")

    if height is not None:
        p.plot_height = height

    if width is not None:
        p.plot_width = width

    if y2 is not None:
        p.extra_y_ranges = y2
        p.add_layout(LinearAxis(y_range_name="y2",
                                axis_label=ldict['y2label']), 'right')

        # Annoyingly, the main y-axis still autoscales if there is a
        #   second y-axis. Setting these means that the axis WON'T
        #   autoscale until they're set back to None
        p.y_range = DataRange1d(start=y1lim[0], end=y1lim[1])

    p.x_range.follow = "end"
    p.x_range.range_padding = 0.1
    p.x_range.range_padding_units = 'percent'

    # Hack! But it works. Need to do this *before* you create cds below!
    #   Includes a special flag (first=True) to pad the beginning so all
    #   the columns in the final ColumnDataSource are the same length
    pix, piy = makePatches(r.index, y1lim, first=True)

    # The "master" data source to be used for plotting.
    #   Generate it via the column names in the now-merged 'r' DataFrame
    #   Start with the 'index' 'pix' and 'piy' since they're always those names
    mds = dict(index=r.index, pix=pix, piy=piy)

    # Start our plot source
    cds = ColumnDataSource(mds)

    # Now loop over the rest of our columns to fill it out, plotting as we go
    cols = r.columns
    lineSet = []
    legendItems = []
    for i, col in enumerate(cols):
        # Add our data to the cds
        cds.add(getattr(r, col), name=col)

        # Make the actual line plot object
        # TODO: Make this search in a given "y2" axis list
        if col.lower() == "humidity":
            lineObj, _ = plotLineWithPoints(p, cds, col, dset[i],
                                            yrname="y2")
        else:
            lineObj, _ = plotLineWithPoints(p, cds, col, dset[i])

        lineSet.append(lineObj)

        # Now make it's corresponding legend item
        legendObj = LegendItem(label=col, renderers=[lineObj])
        legendItems.append(legendObj)

    legend = Legend(items=legendItems,
                    location="bottom_center",
                    orientation='horizontal', spacing=15)
    p.add_layout(legend, 'below')

    # Customize the active tools
    p.toolbar.autohide = True

    # HACK HACK HACK HACK HACK
    #   Apply the patches to carry the tooltips
    #
    # Shouldn't I just stream this instead of pix/nix and piy/niy ???
    #
    simg = p.patches('pix', 'piy', source=cds,
                     fill_color=None,
                     fill_alpha=0.0,
                     line_color=None)

    # This will also create the tooltips for each of the entries in cols
    ht = createHoverTool(simg, cols)
    p.add_tools(ht)

    return p, cds, cols


def createHoverTool(simg, cols):
    """
    """
    # Make the hovertool only follow the patches (still a hack)
    htline = simg

    ht = HoverTool()
    ht.tooltips = [("Time", "@index{%F %T}")]
    for col in cols:
        fStr = "@%s{0.00}" % (col)
        ht.tooltips.append((col, fStr))

    ht.formatters = {'index': 'datetime'}
    ht.show_arrow = False
    ht.point_policy = 'follow_mouse'
    ht.line_policy = 'nearest'
    ht.renderers = [htline]

    return ht


def makeNewPatches(nf, y1lim, lastTimedt):
    """
    Make a new set of patches based on the stuff in the 'nf' Dataframe.

    This is most useful when stream()ing new data to an already
    existing ColumnDataSource.

    There is some special handling necessary for the case where we just
    have one new point in time, since makePatches assumes that you give
    it enough to sketch out a box.  It could be changed so it makes
    the last box the full xwidth, and that it's .patch()'ed on update
    here to always be correct.  But, that's a little too complicated right now.

    This is generally confusing without a diagram. Sorry.
    """
    numRows = nf.shape[0]
    if numRows == 1:
        print("Single row!")

        nidx = [pd.Timestamp(lastTimedt), nf.index[-1]]
        nix, niy = makePatches(nidx, y1lim)
        fix = [nf.index[-1]]

        print("Made patches")
        print(np.shape(nix), np.shape(niy), np.shape(fix))
    else:
        print("Multirow!")

        nidx = [pd.Timestamp(lastTimedt)] + list(nf.index)
        nix, niy = makePatches(nidx, y1lim)
        fix = nidx[:-1]

        print("Made patches")
        print(np.shape(nix), np.shape(niy), np.shape(fix))

    return nix, niy


def makePatches(xindex, y1lim, first=False):
    """
    This is a bit of a HACK!  It might be a little screwy at the edges.

    It gives way better tooltips on a timeseries plot.  It works by
    turning the indicies into a list of lists of x coordinates and
    y coordinates for a series of adjacent patches.  Their width is the time
    between two datapoints and height spans the (initial) y1 range.
    """
    ix = []
    iy = []

    if len(xindex) < 2:
        print("ERROR: Need at least two xindex values!")
        raise ValueError

    if len(y1lim) != 2:
        print("ERROR: Need exactly two y1lim values!")
        raise ValueError

    for i, _ in enumerate(xindex):
        store = False
        # NOTE: Life is just easier if we make sure to keep things in
        #   terms of pandas.Timestamp from this point forward, since
        #   this will ultimately be stream()'ed back into the
        #   original plot's ColumnDataSource, which was really a
        #   pandas.DataFrame at the start of it's life
        if i == 0:
            if first is True:
                # Special case for the very first row of data the first
                #   time we make the hacked patches; we pad out the xrange
                #   so the first value is shown.  Subsequent calls
                #   MUST be first=False or else things will go poorly, quickly
                # It's small enough to hit, but not large enough to screw with
                #   the auto-scaled x range.  Or at least that's the intent!
                x1 = pd.Timestamp(xindex[0])
                x0 = x1 - pd.Timedelta(seconds=60)
                store = True
        else:
            x0 = pd.Timestamp(xindex[i-1])
            x1 = pd.Timestamp(xindex[i])
            store = True

        if store is True:
            ix.append([x0, x1, x1, x0])
            iy.append([y1lim[0], y1lim[0], y1lim[1], y1lim[1]])

    return ix, iy


def plotLineWithPoints(p, cds, sname, color,
                       hcolor=None, yrname=None):
    """
    p: plot object
    cds: ColumnDataSource
    sname: source name (in cds)
    slabel: series label (for legend)
    Assumes that you have both 'index' and sname as columns in your
    ColumnDataSource! slabel is then used for the Legend and tooltip labels.
    """
    # NOTE: The way my polling code is set up, mode='after' is the correct
    #   step mode since I get the result and then sleep for an interval
    if hcolor is None:
        hcolor = '#E24D42'

    if yrname is None:
        ln = p.step('index', sname, line_width=2, source=cds, mode='after',
                    color=color, name=sname)
        sc = p.scatter('index', sname, size=8, source=cds,
                       color=color, name=sname,
                       alpha=0., hover_alpha=1., hover_color=hcolor)
    else:
        ln = p.step('index', sname, line_width=2, source=cds, mode='after',
                    y_range_name=yrname,
                    color=color, name=sname)
        sc = p.scatter('index', sname, size=8, source=cds,
                       y_range_name=yrname,
                       color=color, name=sname,
                       alpha=0., hover_alpha=1., hover_color=hcolor)

    return ln, sc


def createSunAnnotations(qdata):
    """
    """
    # Highlight the sunrise/sunset times. Hackish.
    srt = qdata['ephemera'].sunrise.tail(1).values[0]
    sunrise = Span(location=srt, name='sunrise',
                   dimension='height', line_color='red',
                   line_dash='dashed', line_alpha=0.75, line_width=3)

    sst = qdata['ephemera'].sunset.tail(1).values[0]
    sunset = Span(location=sst, name='sunset',
                  dimension='height', line_color='green',
                  line_dash='dashed', line_alpha=0.75, line_width=3)

    return sunrise, sunset


def newDataCallback(cds, cols, nf, lastTimedt, y1lim):
    """
    """
    if nf.size == 0:
        print("No new data.")
        mds2 = {}
    else:
        # At this point, there might be a NaN in the column(s) from rf2.
        #   Since we stream only the NEW values, we need to be nice to
        #   ourselves and fill in the prior value for those columns so
        #   the tooltips function and don't spaz out. So get the final
        #   values manually and then fill them into those columns.
        cfills = {}
        for col in cols:
            fillVal = helpers.getLastVal(cds, col)
            cfills.update({col: fillVal})
        print(cfills)

        # Fill in our column holes. If there are *multiple* temporal holes,
        #   it'll look bonkers because there's only one fill value.
        nf.fillna(value=cfills, inplace=True)

        # Create the patches for the *new* data only
        nix, niy = makeNewPatches(nf, y1lim, lastTimedt)

        # It is VITALLY important that the length of all of these
        #   is the same! If it's not, it'll slowly go bonkers.
        #
        # Before this is streamed to the main column data source, bokeh
        #   attempts to convert it to an ndarray. But it screws up the
        #   index.  So take care of that ourselves here.
        mds2 = dict(index=nf.index.to_numpy(), pix=nix, piy=niy)
        print("mds2 now contains:", mds2)

        for col in cols:
            print(col)
            # We need to make sure the update matches the timestamp format
            #   that is likely already in the original dataset, namely
            #   nanoseconds since epoch.  col is the index, which is
            #   of type pandas.Timestamp() so convert it to nanoseconds!
            # storableTimestamp = mds2[col].timestamp()*1e6
            pandasObject = getattr(nf, col)
            # Change the dtype of the index/timestamp so it's more consistent
            pandasObject.index = pandasObject.index.values.view('int64')
            mds2.update({col: pandasObject})

    print("Final mds2:", mds2)

    return mds2

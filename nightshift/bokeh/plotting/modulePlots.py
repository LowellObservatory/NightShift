# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 4 Dec 2018
#
#  @author: rhamilton

"""Collection of routines used to make good Bokeh plots.

I admit it's a big damn mess in here.  This really needs to be cleaned
up in the near future, and streamlined to align to the new containerized
way that the plots are called/generated/updated.  A lot of this code could
turn out to be vestigial from the initial version that made plot snapshots.
    - RTH 20190426
"""

from __future__ import division, print_function, absolute_import

import random
import datetime as dt

import numpy as np
import pandas as pd
from pytz import timezone

from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import Span, DataRange1d, LinearAxis,\
                         Legend, LegendItem, HoverTool,\
                         DataTable, TableColumn, HTMLTemplateFormatter


class valJudgement(object):
    def __init__(self):
        self.label = None
        self.value = None
        self.timestamp = None
        self.tooOld = True
        self.likelyInvalid = True

    def judgeAge(self, oldAge=None, maxAge=None, compTime=None):
        # Need to put everything into Numpy datetime64/timedelta64 objects
        #   to allow easier interoperations
        if maxAge is None:
            maxAge = dt.timedelta(hours=2.)
            maxAge = np.timedelta64(maxAge)
        if oldAge is None:
            oldAge = dt.timedelta(minutes=5.5)
            oldAge = np.timedelta64(oldAge)

        if compTime is None:
            compTime = np.datetime64(dt.datetime.utcnow())

        delta = compTime - self.timestamp
        if delta > oldAge:
            self.tooOld = True
        else:
            self.tooOld = False

        if delta > maxAge:
            self.likelyInvalid = True
        else:
            self.likelyInvalid = False


def funnyValues():
    """
    """
    # Have some fun with it at least
    ustrs = ["inconceivable", "implausible", "improbable",
             "unknown", "unfathomable",
             "unimaginable", "unknowable", "unclear",
             "mind-boggling"]

    retValue = random.choice(ustrs).upper()

    return retValue


def setupTable(cds):
    """
    """
    # Define our color format/template
    #   This uses Underscore’s template method and syntax.
    #   http://underscorejs.org/#template
    template = """
                <b>
                <div style="background:<%=
                    (function ageColorer(){
                        if(ageStatement){
                        return("#ff0000;opacity:0.25;")
                        }
                        else{
                        return("none;")
                        }
                    }()) %>;">
                    <%= value %>
                </div>
                </b>
                """

    formatter = HTMLTemplateFormatter(template=template)

    # Now we construct our table by specifying the columns we actually want.
    #   We ignore the 'ageStatement' row for this because we
    #   just get at it via the formatter/template defined above
    labelCol = TableColumn(field='labels', title='Parameter', sortable=False)
    valueCol = TableColumn(field='values', title='Value', sortable=False,
                           formatter=formatter)
    cols = [labelCol, valueCol]

    nRows = len(cds.data['labels'])

    # Now actually construct the table
    dtab = DataTable(columns=cols, source=cds)

    # THIS IS SO GOD DAMN IRRITATING
    #   It won't accept this in a theme file because it seems like there's a
    #   type check on it and 'None' is not the 'correct' type
    dtab.index_position = None

    # This is also irritating
    #   Specify a css group to be stuffed into the resulting div/template
    #   which is then styled by something else. Can't get it thru the theme :(
    dtab.css_classes = ["nightwatch_bokeh_table"]

    return dtab, nRows


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
            fillVal = getLastVal(cds, col)
            cfills.update({col: fillVal})

        # Fill in our column holes. If there are *multiple* temporal holes,
        #   it'll look bonkers because there's only one fill value.
        nf.fillna(value=cfills, inplace=True)

        # Create the patches for the *new* data only
        nix, niy = makeNewPatches(nf, y1lim, lastTimedt)

        # It is VITALLY important that the length of all of these
        #   is the same! If it's not, it'll slowly go bonkers.
        #
        # Could add a check to make sure here, but I'll ride dirty for now.
        mds2 = dict(index=nf.index, pix=nix, piy=niy)
        for col in cols:
            mds2.update({col: getattr(nf, col)})

    return mds2


def convertTimestamp(lastTime, tz='UTC'):
    """
    """
    if tz.upper() == 'UTC':
        storageTZ = timezone('UTC')
    else:
        raise NotImplementedError

    # It's possible that the timestamp class/type shifts slightly as we
    #   stream data into the main CDS; do some sanitization to check
    #   that we're not going to suddenly barf because of that.
    try:
        # warn=False because I strip the nanoseconds out of everything
        #   ... eventually.  Remember that 'warn' is only valid on an
        #   individual Timestamp object, not the DatetimeIndex as a whole!
        lastTimedt = lastTime.to_pydatetime(warn=False)
    except AttributeError:
        # This means it wasn't a Timestamp object, and it doesn't have
        #   the method that we want/desire.
        if isinstance(lastTime, np.datetime64):
            # A bit silly, but since pandas Timestamp is a subclass of
            #   datetime.datetime and speaks numpy.datetime64
            #   this is the easiest thing to do
            lastTimeTimestamp = pd.Timestamp(lastTime)
            lastTimedt = lastTimeTimestamp.to_pydatetime(warn=False)

            # The server timezone has been set (during its setup) to UTC;
            #   we need to specifically add that to avoid timezone
            #   shenanigans because in a prior life we were bad and
            #   apparently now must be punished
            lastTimedt = lastTimedt.replace(tzinfo=storageTZ)
            # print("Converted %s to %s" % (lastTime, lastTimedt))
        elif isinstance(lastTime, str):
            # Ok, easy enough, it's a datetime stamp in string form
            try:
                lastTimedt = dt.datetime.strptime(lastTime,
                                                  "%Y-%m-%d %H:%M:%S.%f %Z")
                lastTimedt = lastTimedt.replace(tzinfo=storageTZ)
            except Exception:
                print("BAD TIMESTAMP FORMAT!")
                raise NotImplementedError
        else:
            print("IDK WTF BBQ")
            print("Unexpected timestamp type:", type(lastTime))
            raise NotImplementedError

    return lastTimedt


def getLastVal(cds, cdstag):
    """
    Given a ColumnDataSource (or numpy array) return the last value.

    Mostly useful to grab a quick-and-dirty 'fill' value when combining
    multiple independent sources.

    Does not check if that last value is actually a NaN, which is probably
    a bad thing to ignore.  But that could be fixed too.
    """
    # Default/failsafe value
    fVal = np.nan

    try:
        # This means that the data are a pandas Series
        fVal = cds.data[cdstag].values[-1]
    except AttributeError:
        # This means that the data are really just an array now
        fVal = cds.data[cdstag][-1]

    return fVal


def getLast(p1, fieldname, label=None, lastIdx=None, compTime=None,
            scaleFactor=None, fstr=None, nullVal=None):
    """
    """
    retObj = valJudgement()

    # If it's empty, we can just cut to the chase
    if not isinstance(p1, pd.DataFrame):
        # Give it a default value
        if nullVal is None:
            retObj.value = funnyValues()
        else:
            retObj.value = nullVal

        # Give it a default timestamp
        retObj.timestamp = pd.Timestamp(0, unit='s', tz='UTC').to_datetime64()

        # We already know that it's out of date
        retObj.tooOld = True
        retObj.likelyInvalid = True

        # Give it a default label
        if label is not None:
            retObj.label = label
        else:
            retObj.label = fieldname
    else:
        # Get the last valid position/value in the dataframe
        lastIdx = p1.index[-1]

        val = getattr(p1, fieldname)[lastIdx]
        if scaleFactor is not None:
            sValue = val*scaleFactor
        else:
            sValue = val

        if fstr is None:
            retObj.value = sValue
        else:
            retObj.value = fstr % (sValue)

        # Use datetime64 to avoid an annoying nanoseconds warning when
        #   using just regular .to_pydatetime()
        retObj.timestamp = lastIdx.to_datetime64()

        if label is not None:
            retObj.label = label
        else:
            retObj.label = fieldname

        retObj.judgeAge(compTime=compTime)
        if retObj.likelyInvalid is True:
            if nullVal is None:
                retObj.value = funnyValues()
            else:
                retObj.value = nullVal

    return retObj


def deshred(plist, failVal=-1, delim=":", name=None):
    """
    NOTE: p0 thru 2 are expected to be valJudgement objects obtained by
    something like the getLast function!
    """
    # Just use the properties from the first one and assume the rest follow
    #   in terms of whether they were too old or not
    fObj = valJudgement()
    fObj.timestamp = plist[0].timestamp
    fObj.tooOld = plist[0].tooOld

    rstr = ""
    for i, each in enumerate(plist):
        # Catch an invalid value and escape early, so we can write just
        #   one "bad" value in it
        # if each.value == failVal:
        if each.likelyInvalid is True:
            break
        else:
            # Smoosh it all together; if it's the last value, don't
            #   add the delim since it's not needed at the end of the str
            if i == len(plist) - 1:
                delim = ""

            try:
                rstr += "%02d%s" % (each.value, delim)
            except TypeError:
                # This means we probably had heterogeneous datatypes so just
                #   print them all as strings to move on quickly
                rstr += "%s%s" % (each.value, delim)

    if name is None:
        # Don't really have a good default here so just use the first one
        fObj.label = plist[0].label
    else:
        fObj.label = name

    if rstr != "":
        fObj.value = rstr
    else:
        fObj.value = funnyValues()

    return fObj


def checkForEmptyData(indat):
    """
    """
    # Check to make sure we actually have data ...
    abort = False
    for q in indat:
        if len(indat[q]) == 0:
            abort = True
            break

    return abort


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
        l = p.step('index', sname, line_width=2, source=cds, mode='after',
                   color=color, name=sname)
        s = p.scatter('index', sname, size=8, source=cds,
                      color=color, name=sname,
                      alpha=0., hover_alpha=1., hover_color=hcolor)
    else:
        l = p.step('index', sname, line_width=2, source=cds, mode='after',
                   y_range_name=yrname,
                   color=color, name=sname)
        s = p.scatter('index', sname, size=8, source=cds,
                      y_range_name=yrname,
                      color=color, name=sname,
                      alpha=0., hover_alpha=1., hover_color=hcolor)

    return l, s

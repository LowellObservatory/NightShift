# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 4 Dec 2018
#
#  @author: rhamilton

"""Collection of helper routines used when making plots.

I admit it's a bit of a mess.

This really needs to be cleaned further, since there are some
duplications in functionality and some functions that need to be refactored.
    - RTH 20190531
"""

from __future__ import division, print_function, absolute_import

import random
import datetime as dt

import numpy as np
import pandas as pd
from pytz import timezone


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
             "ineffable", "indescribable",
             "unknown", "unfathomable", "unspeakable",
             "unimaginable", "unknowable", "unclear",
             "mind-boggling"]

    retValue = random.choice(ustrs).upper()

    return retValue


def convertTimestamp(lastTime, tz='UTC'):
    """
    """
    if tz.upper() == 'UTC':
        storageTZ = timezone('UTC')
    else:
        raise NotImplementedError

    print("Converting timestamp", lastTime, "of type", type(lastTime))

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
    Remember: fstr is a FORMAT string! Can be used to add units,
    control precision, etc.
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
        # At least what we given was a DataFrame...but we need to dig deeper

        # Get the last valid position/value in the dataframe
        lastIdx = p1.index[-1]

        # Make sure we can actually find the data; it could be empty
        #   if there wasn't anything found within the queried time range!
        try:
            val = getattr(p1, fieldname)[lastIdx]
            if scaleFactor is not None:
                sValue = val*scaleFactor
            else:
                sValue = val

            # Use datetime64 to avoid an annoying nanoseconds warning when
            #   using just regular .to_pydatetime()
            retObj.timestamp = lastIdx.to_datetime64()

            # Deal with any requested formatting changes
            if fstr is None or sValue is None:
                retObj.value = sValue
            else:
                retObj.value = fstr % (sValue)

            # Set the label used in the table (or whatever)
            if label is not None:
                retObj.label = label
            else:
                retObj.label = fieldname

            # One last sanity check - it's possible we got this far but the
            #   value is really just a NaN.  This check should probably be
            #   rolled into judgeAge for safety as well as future sanity.
            #   We use the Pandas check here because it returns a single
            #   value, whereas the Numpy version returns an array
            # We also need to check for instances where NaN got stringed
            if retObj.value == 'nan':
                retObj.value = np.nan
            retObj.likelyInvalid = pd.isna(retObj.value)
        except (TypeError, AttributeError):
            # The TypeError catch will get triggered on queries where there
            #   is no data and I fudged a returned DataFrame because
            #   val*scaleFactor will explode, or the fstr did.
            retObj.likelyInvalid = True

        if retObj.likelyInvalid is True:
            sValue = None
            retObj.tooOld = True
            retObj.likelyInvalid = True
            retObj.timestamp = np.datetime64('1983-04-15T02:00')

            if nullVal is None:
                retObj.value = funnyValues()
            else:
                retObj.value = nullVal
        else:
            # This means everything up to this point was ok, so
            #    do the nominal check on it's age/vintage and give it back
            retObj.judgeAge(compTime=compTime)

    return retObj


def deshred(plist, failVal=-1, delim=":", name=None):
    """
    NOTE: p0 thru 2 are expected to be valJudgement objects obtained by
    something like the getLast function!
    """
    # Just use the properties from the first one and assume the rest follow
    #   in terms of whether they were too old or not
    fObj = valJudgement()

    # Start with the values in the very first one
    fObj.timestamp = plist[0].timestamp
    fObj.tooOld = plist[0].tooOld
    fObj.likelyInvalid = plist[0].likelyInvalid

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

# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 6 Nov 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import datetime as dt

import pytz
import pandas as pd
from influxdb import DataFrameClient


def queryConstructor(dbq, debug=False):
    """
    dbq is type databaseQuery, which includes databaseConfig as
    dbq.db.  More info in 'confHerder'.

    dtime is time from present (in hours) to query back

    Allows grouping of the results by a SINGLE tag with multiple values.
    No checking if you want all values for a given tag, so be explicit for now.
    """
    if isinstance(dbq.rangehours, str):
        try:
            dtime = int(dbq.rangehours)
        except ValueError:
            print("Can't convert %s to int!" % (dbq.rangehours))
            dtime = 1

    if dbq.database.type.lower() == 'influxdb':
        if debug is True:
            print("Searching for %s in %s.%s on %s:%s" % (dbq.fields,
                                                          dbq.tablename,
                                                          dbq.metricname,
                                                          dbq.database.host,
                                                          dbq.database.port))

        # Some renames since this was adapted from an earlier version
        tagnames = dbq.tagnames
        if tagnames is not None:
            tagvals = dbq.tagvals
        else:
            tagvals = []

        # TODO: Someone should write a query validator to make sure
        #   this can't run amok.  For now, make sure the user has
        #   only READ ONLY privileges to the database in question!!!
        query = 'SELECT'
        if isinstance(dbq.fields, list):
            for i, each in enumerate(dbq.fields):
                # Catch possible fn/dn mismatch
                try:
                    query += ' "%s" AS "%s"' % (each.strip(),
                                                dbq.fieldlabels[i])
                except IndexError:
                    query += ' "%s"' % (each.strip())
                if i != len(dbq.fields)-1:
                    query += ','
                else:
                    query += ' '
        else:
            if dbq.fieldlabels is not None:
                query += ' "%s" AS "%s" ' % (dbq.fields, dbq.fieldlabels)
            else:
                query += ' "%s" ' % (dbq.fields)

        query += 'FROM "%s"' % (dbq.metricname)
        query += ' WHERE time > now() - %02dh' % (dtime)

        if tagvals != []:
            query += ' AND ('
            if isinstance(dbq.tagvals, list):
                for i, each in enumerate(tagvals):
                    query += '"%s"=\'%s\'' % (tagnames, each.strip())

                    if i != len(tagvals)-1:
                        query += ' OR '
                query += ') GROUP BY "%s"' % (tagnames)
            else:
                # If we're here, there was only 1 tag value so we don't need
                #   to GROUP BY anything
                query += '"%s"=\'%s\')' % (tagnames, tagvals)

        return query


def getResultsDataFrame(query, debug=False):
    """
    Attempts to distinguish queries that have results grouped by a tag
    vs. those which are just of multiple fields. May be buggy still.
    """
    querystr = queryConstructor(query, debug=debug)

    # Line length/clarity control
    db = query.database
    idfc = DataFrameClient(host=db.host, port=db.port,
                           username=db.user,
                           password=db.password,
                           database=query.tablename)

    results = idfc.query(querystr)

    # results is a dict of dataframes, but it's a goddamn mess. Clean it up.
    betterResults = {}

    # Get the names of the expected columns
    expectedCols = query.fieldlabels

    if results != {}:
        # If all went well, results.keys() should be the same as
        #   query.metricname; if I do this right I can hopefully
        #   ditch the first for loop below?
        rframe = results[query.metricname]

        for rkey in results.keys():
            # If you had a tag that you "GROUP BY" in the query, you'll now
            #   have a tuple of the metric name and the tag + value pair.
            #   If you had no tag to group by, you'll have just the
            #   flat result.
            if isinstance(rkey, tuple):
                # Someone tell me again why Pandas is so great?
                #   I suppose it could be jankiness in influxdb-python?
                #   This magic 'tval' line below is seriously dumb though.
                tval = rkey[1][0][1]
                dat = results[rkey]
                betterResults.update({tval: dat})
            elif isinstance(rkey, str):
                betterResults = results[rkey]

        # Check to make sure all of the expected columns are in our frame
        cols = betterResults.columns.to_list()
        for ecol in expectedCols:
            if ecol not in cols:
                print("Missing column %s in result set!" % (ecol))
                betterResults[ecol] = None
            else:
                print("Found column %s in result set." % (ecol))
    else:
        # This means that the query literally returned nothing at all, so
        #   we have to make the expected DataFrame ourselves so others
        #   don't crash outright. We need to make sure the index of the
        #   dataframe is of type DateTimeIndex as well so future screening
        #   doesn't barf due to missing methods.
        print("Query returned no results! Is that expected?")
        utctz = pytz.timezone(("UTC"))
        now = dt.datetime.now().astimezone(utctz)

        betterResults = pd.DataFrame()

        if isinstance(expectedCols, str):
            # NEED a dict here with a timestamp as key so the Dataframe
            #   index is of the right type later on
            betterResults[expectedCols] = {now: None}
        elif isinstance(expectedCols, list):
            for ecol in expectedCols:
                betterResults[ecol] = {now: None}

        # utctz = pytz.timezone(("UTC"))
        # now = dt.datetime.now().astimezone(utctz)
        # betterResults.set_index(pd.DatetimeIndex([now]))

    # This is at least a little better
    return betterResults

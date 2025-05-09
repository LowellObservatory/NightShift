# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 26 Dec 2018
#
#  @author: rhamilton

"""
"""

from __future__ import division, print_function, absolute_import

import logging
from typing import Optional
from datetime import datetime as dt
from collections import OrderedDict

import pkg_resources as pkgr

from bokeh.themes import Theme
from bokeh.plotting import curdoc
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler

from tornado.ioloop import PeriodicCallback

from ligmos.utils import ephemera
from ligmos.utils import database

import nightshift.bokeh.confHerder as ch
import nightshift.bokeh.plotting.colorWheelies as cwheels

from nightshift.bokeh.ldt import facsumLPI, facsumTCS
from nightshift.bokeh.ldt import ldtWeather, ldtWeatherTable
from nightshift.bokeh.ldt import ldtWind, ldtWindTable


# Make sure all the endpoints work from the same base document.
#   This is also where we stash the plot data
doc = curdoc()


class masterPlotState():
    def __init__(self):
        self.data = None
        self.theme = None
        self.colors = None
        self.modules = None
        self.queries = None
        self.timestamp = None


def batchQuery(plotState=None, site='ldt', debug=False):
    """
    It's important to do all of these queries en-masse, otherwise the results
    could end up being confusing - one plot's data could differ by
    one (or several) update cycle times eventually, and that could be super
    confusing and cause users to think that things like coordinates are
    not right when it's really just our view of them that has drifted.

    By doing them all at once or in quick succession, it's more likely
    that we'll capture the same instantaneous 'state' of the telescope/site.
    """
    qdata = OrderedDict()

    if plotState is None:
        quer = doc.template.globals['plotState'].queries
    else:
        quer = plotState.queries

    for iq in quer.keys():
        # q = quer[iq]
        # Should not only pull this out of the loop, but change it to
        #   use 'bind_params' for extra safety!
        # query = dbq.queryConstructor(q, dtime=q.rangehours, debug=debug)
        td = database.getResultsDataFrame(quer[iq], debug=debug)

        qdata.update({iq: td})

    dts = dt.utcnow()
    print("%d queries complete!" % (len(qdata)))

    # Create pyEphem object at the above for the current time
    #   Doing it in a class so it can also contain the solarsystemAngles too
    #   along with anything else we decide we need later on
    obsSite = ephemera.observingSite(sitename=site)

    # Translate all those times and angles into a dataframe that we can
    #   then stuff into our hiding spot with all the other things
    edf = obsSite.toPandasDataFrame()
    qdata.update({'ephemera': edf})

    print("Data stored at %s" % (dts))

    # Put the plotState into the server document root so the plotting routines
    #   can actually access the stuff they need
    # TODO: Figure this shit out.
    if plotState is not None:
        # Update our class, then stash it
        plotState.data = qdata
        plotState.timestamp = dts

        # Here's the sneaky stash!
        doc.template.globals.update({'plotState': plotState})
        print("Data stashed in doc.template.globals.")
    else:
        # We already stashed, so just update the changed bits
        doc.template.globals['plotState'].data = qdata
        doc.template.globals['plotState'].timestamp = dts


def configServer():
    """
    """
    # LOOP OVER THE CONFIG TO MAKE THIS
    ldtWeatherFunc = FunctionHandler(ldtWeather.make_plot)
    ldtWeatherApp = Application(ldtWeatherFunc)

    ldtWeatherTableFunc = FunctionHandler(ldtWeatherTable.makeTable)
    ldtWeatherTableApp = Application(ldtWeatherTableFunc)

    ldtWindFunc = FunctionHandler(ldtWind.make_plot)
    ldtWindApp = Application(ldtWindFunc)

    ldtWindTableFunc = FunctionHandler(ldtWindTable.makeTable)
    ldtWindTableApp = Application(ldtWindTableFunc)

    facsumTCSFunc = FunctionHandler(facsumTCS.makeFacSum)
    facsumTCSApp = Application(facsumTCSFunc)

    facsumLPIFunc = FunctionHandler(facsumLPI.makeFacSum)
    facsumLPIApp = Application(facsumLPIFunc)

    apps = {'/ldtweather': ldtWeatherApp,
            '/ldtweathertable': ldtWeatherTableApp,
            '/ldtwind': ldtWindApp,
            '/ldtwindtable': ldtWindTableApp,
            '/facsum_tcs': facsumTCSApp,
            '/facsum_lpi': facsumLPIApp}

    print("Starting bokeh server...")
    server = Server(apps, port=5000,
                    allow_websocket_origin=['127.0.0.1:8000',
                                            '127.0.0.1:5000',
                                            'localhost:5000',
                                            'localhost:8000',
                                            'dctsleeperservice:5000',
                                            'dctsleeperservice:9876',
                                            'nightwatch',
                                            'nightwatch.lowell.edu',
                                            'nightwatch.lowell.local'])

    return server


if __name__ == "__main__":
    # Can spin these off to configParser things later
    qconff = './config/dbqueries.conf'
    mconff = './config/modules.conf'

    # Grab the default theme in the least painful way possible
    #   We have to do it here because this is where curdoc lives/dies
    themefile = pkgr.resource_filename('nightshift',
                                       "resources/bokeh_dark_theme.yml")

    # Parse the configuration files
    #   'mods' is a list of ch.moduleConfig objects.
    #   'quer' is a list of all the active database sections associated
    mods, quer = ch.parser(qconff, mconff)

    # Create the bokeh theme object to be applied in the actual documents
    theme = Theme(filename=themefile)

    # Get the default color sets; second one is sorted by hue but
    #   I'm ditching it since I'm not using it
    dset, _ = cwheels.getColors()

    # Set up logging to a file
    # We need to make a handler that rotates ourselves, and then attach it.
    #   Cribbed from ligmos.utils.logs.setup_logging()
    print("Sending the output to the file")
    logName = './outputs/logs/bokehmcbokehface.log'
    nLogs = 10
    handler = logging.handlers.TimedRotatingFileHandler(logName,
                                                        when="midnight",
                                                        utc=True,
                                                        backupCount=nLogs)
    # Format each log message like this
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    # Attach the formatter to the handler
    handler.setFormatter(formatter)
    # Attach the handler to the logger.
    #   Cribbed from bokeh.util.logconfig
    level = 'DEBUG'
    default_handler: Optional[logging.Handler] = None
    bokeh_logger = logging.getLogger('bokeh')
    bokeh_logger.removeHandler(default_handler)
    bokeh_logger.setLevel(level)
    bokeh_logger.addHandler(handler)
    bokeh_logger.propagate = True

    # Now pack it all into a nice class that can be added to the
    #   main doc to be inherited by each plot that we make
    plotState = masterPlotState()

    # TODO: Make this possible in __init__ by passing in **kwargs
    plotState.theme = theme
    plotState.colors = dset
    plotState.modules = mods
    plotState.queries = quer

    # Go and get our initial state of data. Give it the masterPlotState
    #   class so it can be initially stashed in the doc template
    batchQuery(plotState=plotState, debug=True)

    # Set up the server
    server = configServer()

    # Set up the data-refreshing periodic callback
    # NOTE: jitter=0.1 means the callback will be called at intervals +- 10%
    #   to avoid constant clashes with other periodic processes
    pcallback = PeriodicCallback(batchQuery, 60000, jitter=0.1)
    print("Starting server ioloop periodic callback")
    pcallback.start()

    # Actually start the server
    server.start()
    server.io_loop.start()

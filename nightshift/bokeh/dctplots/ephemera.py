# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 9 May 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import ephem
import numpy as np
import pandas as pd
from pytz import timezone


class observingSite():
    def __init__(self, sitename='dct'):
        self.eObserver = None
        self.sunmoon = None

        if sitename.lower() == 'dct':
            # Remaking the observer here updates the time automagically for us.
            #   Could change the date/time manually, but this is fine for now.
            self.eObserver = ephem.Observer()
            self.eObserver.lat = '34.7443'
            self.eObserver.lon = '-111.4223'
            self.eObserver.elevation = 2361
            self.eObserver.name = "Lowell Observatory DCT"

            # Go ahead and calculate all the angles/times we care about
            self.sunmoon = solarsystemAngles(self.eObserver)
        else:
            print("UNKNOWN OBSERVATORY SITE! ABORTING.")
            raise NotImplementedError

    def toPandasDataFrame(self):
        """
        Convienent way to pack up the things we care about into a Pandas
        DataFrame for stashing elsewhere
        """
        colNames = ['sunrise', 'nextsunrise',
                    'sunset', 'nextsunset',
                    'sun_dms', 'moon_dms', 'moonphase']

        # Loop over these and make a dict as we go
        ddict = {}
        for col in colNames:
            entry = {col: getattr(self.sunmoon, col)}
            ddict.update(entry)

        # Thankfully, pyephem always uses UTC. So add that tzinfo just
        #   so we can compare stuff without warnings/exceptions later on
        index = self.eObserver.date.datetime()
        storageTZ = timezone('UTC')
        index = index.replace(tzinfo=storageTZ)

        return pd.DataFrame(data=ddict, index=[index])


class solarsystemAngles():
    def __init__(self, obssite, autocalc=True):
        self.site = obssite

        self.sun = ephem.Sun()
        self.sun_alt = None
        self.sun_dms = None
        self.sunrise = None
        self.nextsunrise = None
        self.sunset = None
        self.nextsunset = None

        self.moon = ephem.Moon()
        self.moon_alt = None
        self.moon_dms = None
        self.moonphase = None

        if autocalc is True:
            self.updateSunInfo()
            self.updateMoonInfo()

    def updateSunInfo(self):
        """
        """
        self.sun.compute(self.site)
        self.sun_alt = self.sun.alt
        self.sun_dms = np.degrees(ephem.degrees(self.sun_alt))
        self.sunrise = self.sun.rise_time.datetime()
        self.nextsunrise = self.site.next_rising(self.sun).datetime()
        self.sunset = self.sun.set_time.datetime()
        self.nextsunset = self.site.next_setting(self.sun).datetime()

    def updateMoonInfo(self):
        """
        """
        self.moon.compute(self.site)
        self.moon_alt = self.moon.alt
        self.moon_dms = np.degrees(ephem.degrees(self.moon_alt))
        self.moonphase = self.moon.moon_phase

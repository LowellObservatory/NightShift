# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 17 May 2019
#
#  @author: rhamilton

"""Main loop for NEXRAD plotting service.
"""

from __future__ import division, print_function, absolute_import

import os
import time
from datetime import datetime as dt

from ligmos.utils import logs

import nexrad_aws as naws
import plotNEXRAD as pnrad

import common as com
import commonMapping as commap


def main(outdir, creds, sleep=150., keephours=24.,
         forceDown=False, forceRegen=False):
    """
    'outdir' is the *base* directory for outputs, stuff will be put into
    subdirectories inside of it.

    'keephours' is the number of hours of data to keep on hand. Old stuff
    is deleted to keep things managable
    """
    aws_keyid = creds['s3_RO']['aws_access_key_id']
    aws_secretkey = creds['s3_RO']['aws_secret_access_key']

    dout = outdir + "/raws/"
    pout = outdir + "/pngs/"
    lout = outdir + "/nows/"
    cfiles = "./shapefiles/cb_2018_us_county_5m/"

    # in degrees; for spatially filtering map shapefiles
    mapcenter = [-111.4223, 34.7443]
    filterRadius = 7.

    # What the base/first part of the output filename will be
    staticname = 'nexrad'

    # Need this for parsing the filename into a dt obj
    dtfmt = "KFSX%Y%m%d_%H%M%S"

    # Prepare some things for plotting so we don't have to do it
    #   forever in the main loop body
    rclasses = ["Interstate", "Federal"]

    # On the assumption that we'll plot something, downselect the full
    #   road database into the subset we want
    print("Parsing road data...")
    print("\tClasses: %s" % (rclasses))

    # roads will be a dict with keys of rclasses and values of geometries
    roads = commap.parseRoads(rclasses,
                              center=mapcenter, centerRad=filterRadius)
    for rkey in rclasses:
        print("%s: %d found within %d degrees of center" % (rkey,
                                                            len(roads[rkey]),
                                                            filterRadius))

    print("Parsing county data...")
    counties = commap.parseCounties(cfiles + "cb_2018_us_county_5m.shp",
                                    center=mapcenter, centerRad=filterRadius)
    print("%d counties found within %d degrees of center" % (len(counties),
                                                             filterRadius))

    # Construct/grab the color map
    gcmap = pnrad.getCmap()

    print("Starting infinite loop...")
    while True:
        # 'keephours' is time (in hours!) to search for new files relative
        #   to the present.
        #   If they exist, they'll be skipped unless forceDown is True
        when = dt.utcnow()
        print("Looking for files!")
        ffiles = naws.NEXRADAWSgrab(aws_keyid, aws_secretkey, when, dout,
                                    timedelta=keephours, forceDown=forceDown)

        print("Found the following files:")
        for f in ffiles:
            print(os.path.basename(f.key))

        print("Making the plots...")
        # TODO: Return the projection coordinates (and a timestamp of them)
        #   so they can be reused between loop cycles.
        nplots = pnrad.makePlots(dout, pout, mapcenter, cmap=gcmap,
                                 roads=roads, counties=counties,
                                 forceRegen=forceRegen)
        print("%03d plots done!" % (nplots))

        # NOTE: I'm literally adding a 'fudge' factor here because the initial
        #   AWS/data query has a resolution of 1 hour, so there can sometimes
        #   be fighting of downloading/deleting/redownloading/deleting ...
        fudge = 1.
        # BUT only do anything if we actually made a new file!
        if nplots > 0:
            dtfmtpng = dtfmt + '.png'
            cpng = com.clearOldFiles(pout, "*.png", when,
                                     maxage=keephours+fudge, dtfmt=dtfmtpng)
            craw = com.clearOldFiles(dout, "*", when,
                                     maxage=keephours+fudge, dtfmt=dtfmt)

            print("%d, %d raw and png files remain within %.1f + %.1f hours" %
                  (len(cpng), len(craw), keephours, fudge))

            print("Copying the latest/last files to an accessible spot...")
            # Since they're good filenames we can just sort and take the last
            #   if there are actually any current ones left of course
            nstaticfiles = 48

            # Move our files to the set of static filenames. This will
            #   check (cpng) to see if there are actually any files that
            #   are new, and if so it'll shuffle the files into the correct
            #   order of static filenames.
            com.copyStaticFilenames(nstaticfiles, lout, staticname, cpng)
        else:
            print("No new files downloaded so skipping all actions.")

        print("Sleeping for %03d seconds..." % (sleep))
        time.sleep(sleep)


if __name__ == "__main__":
    outdir = "./outputs/"
    awsconf = "./awsCreds.conf"
    forceDownloads = False
    forceRegenPlot = False
    logname = './logs/radarlove.log'

    # Set up logging (using ligmos' quick 'n easy wrapper)
    logs.setup_logging(logName=logname, nLogs=30)

    creds = com.parseConfFile(awsconf)

    main(outdir, creds, forceDown=forceDownloads, forceRegen=forceRegenPlot)
    print("Exiting!")

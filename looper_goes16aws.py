# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 26 Nov 2018
#
#  @author: rhamilton

"""Main loop for GOES-16 reprojection and animation service.
"""

from __future__ import division, print_function, absolute_import

import os
import time
from datetime import datetime as dt

from ligmos.utils import logs, confparsers

from nightshift.goes import plot, aws
from nightshift.common import maps, utils


def main(outdir, creds, sleep=150., keephours=24.,
         forceDown=False, forceRegen=False):
    """
    'outdir' is the *base* directory for outputs, stuff will be put into
    subdirectories inside of it.

    'keephours' is the number of hours of data to keep on hand. Old stuff
    is deleted to keep things managable

    (REMOVED FROM CALLING SEQUENCE)
    'vidhours' is the number of hours of data to make into a GIF (or MP4).
    6 hours equates to about 72 images in the video

    Tailored for a single channel/band of output ONLY. To have multiple bands
    outputting to a single directory this NEEDS some restructuring!!!
    """
    vidhours=4.

    aws_keyid = creds['s3_RO']['aws_access_key_id']
    aws_secretkey = creds['s3_RO']['aws_secret_access_key']

    dout = outdir + "/raws/"
    pout = outdir + "/pngs/"
    lout = outdir + "/nows/"
    cfiles = "./nightshift/resources/cb_2018_us_county_5m/"

    # in degrees; for spatially filtering map shapefiles
    mapcenter = [-111.4223, 34.7443]
    filterRadius = 7.

    # Filename to copy the last/latest image into for easier web integration
    #   Ok to just hardcopy these since they'll be staticly named
    vid1 = "%s/g16aws_latest.gif" % (lout)

    # What the base/first part of the output filename will be
    staticname = 'goes16'
    nstaticfiles = 48

    # Need this for parsing the filename into a dt obj
    dtfmt = "%Y%j%H%M%S%f"

    # Prepare some things for plotting so we don't have to do it
    #   forever in the main loop body
    rclasses = ["Interstate", "Federal"]

    # On the assumption that we'll plot something, downselect the full
    #   road database into the subset we want
    print("Parsing road data...")
    print("\tClasses: %s" % (rclasses))

    # roads will be a dict with keys of rclasses and values of geometries
    roads = maps.parseRoads(rclasses,
                            center=mapcenter, centerRad=filterRadius)
    for rkey in rclasses:
        print("%s: %d found within %d degrees of center" % (rkey,
                                                            len(roads[rkey]),
                                                            filterRadius))

    print("Parsing county data...")
    counties = maps.parseCounties(cfiles + "cb_2018_us_county_5m.shp",
                                  center=mapcenter, centerRad=filterRadius)
    print("%d counties found within %d degrees of center" % (len(counties),
                                                             filterRadius))

    # Construct/grab the color map.
    #   Purposefully leaving this hardcoded here for now, because it's
    #   so easy to make a god damn mess of the colormap if you don't know
    #   what you're doing.
    vmin, vmax = 160, 330
    gcmap = plot.getCMap(vmin=vmin, vmax=vmax)

    print("Starting infinite loop...")
    while True:
        # 'keephours' is time (in hours!) to search for new files relative
        #   to the present.
        #   If they exist, they'll be skipped unless forceDown is True
        when = dt.utcnow()
        print("Looking for files!")
        ffiles = aws.GOESAWSgrab(aws_keyid, aws_secretkey, when, dout,
                                 timedelta=keephours, forceDown=forceDown)

        print("Found the following files:")
        for f in ffiles:
            print(os.path.basename(f.key))

        print("Making the plots...")
        # TODO: Return the projection coordinates (and a timestamp of them)
        #   so they can be reused between loop cycles.
        nplots = plot.makePlots(dout, pout, mapcenter, cmap=gcmap,
                                roads=roads, counties=counties,
                                forceRegen=forceRegen)
        print("%03d plots done!" % (nplots))

        # ... Do what the function says! Return a list of current files
        #   which will then be used as the input for the GIF/video
        #
        # NOTE: I'm literally adding a 'fudge' factor here because the initial
        #   AWS/data query has a resolution of 1 hour, so there can sometimes
        #   be fighting of downloading/deleting/redownloading/deleting ...
        fudge = 1.

        # Now we look for old files.  Looking is ok!  We won't actually act
        #   unless there's a valid reason to do so.
        ofiles = dtfmt + "_C13.png"
        curpngs, oldpngs = utils.findOldFiles(pout, "*.png", when,
                                              maxage=keephours+fudge,
                                              dtfmt=ofiles)

        ofiles = dtfmt + "_C13.nc"
        curraws, oldraws = utils.findOldFiles(dout, "*.nc", when,
                                              maxage=keephours+fudge,
                                              dtfmt=ofiles)

        if nplots > 0:
            # Remove the dead/old ones
            #   BUT notice that this is only if we made new files!
            utils.deleteOldFiles(oldpngs)
            utils.deleteOldFiles(oldraws)

            print("%d, %d raw and png files remain within %.1f + %.1f hours" %
                  (len(curraws), len(curpngs), keephours, fudge))

        print("Copying the latest/last files to an accessible spot...")
        # Move our files to the set of static filenames. This will
        #   check (cpng) to see if there are actually any files that
        #   are new, and if so it'll shuffle the files into the correct
        #   order of static filenames.
        # This will stamp files that are > 4 hours old with a warning
        utils.copyStaticFilenames(curpngs, lout,
                                  staticname, nstaticfiles,
                                  errorAge=4., errorStamp=True)

        print("Sleeping for %03d seconds..." % (sleep))
        time.sleep(sleep)


if __name__ == "__main__":
    outdir = "./outputs/goes/"
    awsconf = "./config/awsCreds.conf"
    forceDownloads = False
    forceRegenPlot = False
    logname = './outputs/logs/goesmcgoesface.log'

    # Set up logging (using ligmos' quick 'n easy wrapper)
    logs.setup_logging(logName=logname, nLogs=30)

    creds = confparsers.parseConfFile(awsconf, enableCheck=False)

    main(outdir, creds, sleep=90.,
         forceDown=forceDownloads, forceRegen=forceRegenPlot)

    print("Exiting!")

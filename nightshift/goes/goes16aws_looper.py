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
import glob
import subprocess as subp
import configparser as conf
from shutil import copyfile
from datetime import datetime as dt

import imageio
import imageio.core.util
from ligmos.utils import logs

import goes16_aws as gaws
import plotGOES as pgoes


def movingPictures(inlist, outname, now, videoage=6., dtfmt="%Y%j%H%M%S%f"):
    """
    processing is determined by the file extension; it only knows about
    'gif' and 'mp4' at present!

    'videoage' is in hours
    """
    maxage = videoage * 60. * 60.
    images = []
    fnames = []
    for filename in inlist:
        diff = getFilenameAgeDiff(filename, now, dtfmt=dtfmt)
        if diff < maxage:
            images.append(imageio.imread(filename))
            fnames.append(filename)

    print("%d files found within %d h of now for the moving pictures" %
          (len(images), videoage))

    # Buffer the last few frames to make it not loop in an annoying way
    images += [images[-1]]*13
    fnames += [fnames[-1]]*13

    if outname.lower().endswith("mp4"):
        print("Starting MP4 creation...")
        try:
            # NEED this because imageio is a bit silly at the moment, and
            #   macro_block_size will destroy our logger.  Once
            #   https://github.com/imageio/imageio/issues/376 is closed
            #   this can be revisited.
            # As of 20181128, imageio FFMPEG is pretty useless for this.
            # imageio.mimwrite(outname, images, quality=7)

            # 0.1 sec frame time ==
            vfopts = "fps=10,format=yuv420p,pad=ceil(iw/2)*2:ceil(ih/2)*2"
            ffmpegcall = ["ffmpeg", "-y", "-pattern_type", "glob",
                          "-i", os.path.dirname(fnames[0]) + "/*.png",
                          "-c:v", "libx264",
                          "-vf", vfopts,
                          outname]
            subp.check_call(ffmpegcall)
            print("MP4 saved as %s" % (outname))
        except subp.CalledProcessError as err:
            print("FFMPEG failed!")
            print(err.output)
    elif outname.lower().endswith("gif"):
        print("Starting GIF creation...")
        imageio.mimwrite(outname, images, loop=0, duration=0.100,
                         palettesize=256)
        print("GIF saved as %s" % (outname))


def parseConfFile(filename):
    """
    """
    try:
        config = conf.SafeConfigParser()
        config.read_file(open(filename, 'r'))
    except IOError as err:
        config = None
        print(str(err))
        return config

    sections = config.sections()
    tsections = ' '.join(sections)

    print("Found the following sections in the configuration file:")
    print("%s\n" % tsections)

    return config


def getFilenameAgeDiff(fname, now, dtfmt="%Y%j%H%M%S%f"):
    """
    NOTE: HERE 'maxage' is already in seconds! Convert before calling.
    """
    # Need to basename it to get just the actual filename and not the path
    beach = os.path.basename(fname)
    try:
        dts = dt.strptime(beach.split("_")[0], dtfmt)
        diff = (now - dts).total_seconds()
    except Exception as err:
        # TODO: Catch the right datetime conversion error!
        print(str(err))
        # Make it "current" to not delete it
        diff = 0

    return diff


def clearOldFiles(inloc, fmask, now, maxage=24., dtfmt="%Y%j%H%M%S%f"):
    """
    'maxage' is in hours
    """
    maxage *= 60. * 60.
    flist = sorted(glob.glob(inloc + fmask))

    remaining = []
    for each in flist:
        diff = getFilenameAgeDiff(each, now, dtfmt=dtfmt)
        if diff > maxage:
            print("Deleting %s since it's too old (%.3f hr)" %
                  (each, diff/60./60.))
            try:
                os.remove(each)
            except OSError as err:
                # At least see what the issue was
                print(str(err))
        else:
            remaining.append(each)

    return remaining


def main(outdir, creds, sleep=150., keephours=24., vidhours=4.,
         forceDown=False, forceRegen=False):
    """
    'outdir' is the *base* directory for outputs, stuff will be put into
    subdirectories inside of it.

    'keephours' is the number of hours of data to keep on hand. Old stuff
    is deleted to keep things managable

    'vidhours' is the number of hours of data to make into a GIF (or MP4).
    6 hours equates to about 72 images in the video

    Tailored for a single channel/band of output ONLY. To have multiple bands
    outputting to a single directory this NEEDS some restructuring!!!
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

    # Filename to copy the last/latest image into for easier web integration
    #   Ok to just hardcopy these since they'll be staticly named
    latestname = '%s/g16aws_latest.png' % (lout)
    vid1 = "%s/g16aws_latest.gif" % (lout)
    vid2 = "%s/g16aws_latest.mp4" % (lout)

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
    roads = pgoes.parseRoads(rclasses,
                             center=mapcenter, centerRad=filterRadius)
    for rkey in rclasses:
        print("%s: %d found within %d degrees of center" % (rkey,
                                                            len(roads[rkey]),
                                                            filterRadius))

    print("Parsing county data...")
    counties = pgoes.parseCounties(cfiles + "cb_2018_us_county_5m.shp",
                                   center=mapcenter, centerRad=filterRadius)
    print("%d counties found within %d degrees of center" % (len(counties),
                                                             filterRadius))

    # Construct/grab the color map.
    #   Purposefully leaving this hardcoded here for now, because it's
    #   so easy to make a god damn mess of the colormap if you don't know
    #   what you're doing.
    vmin, vmax = 160, 330
    gcmap = pgoes.getCmap(vmin=vmin, vmax=vmax)

    print("Starting infinite loop...")
    while True:
        # 'keephours' is time (in hours!) to search for new files relative
        #   to the present.
        #   If they exist, they'll be skipped unless forceDown is True
        when = dt.utcnow()
        print("Looking for files!")
        ffiles = gaws.GOESAWSgrab(aws_keyid, aws_secretkey, when, dout,
                                  timedelta=keephours, forceDown=forceDown)

        print("Found the following files:")
        for f in ffiles:
            print(os.path.basename(f.key))

        print("Making the plots...")
        # TODO: Return the projection coordinates (and a timestamp of them)
        #   so they can be reused between loop cycles.
        nplots = pgoes.makePlots(dout, pout, cmap=gcmap,
                                 roads=roads, counties=counties,
                                 forceRegen=forceRegen, irange=[vmin, vmax])
        print("%03d plots done!" % (nplots))

        # ... Do what the function says! Return a list of current files
        #   which will then be used as the input for the GIF/video
        #
        # NOTE: I'm literally adding a 'fudge' factor here because the initial
        #   AWS/data query has a resolution of 1 hour, so there can sometimes
        #   be fighting of downloading/deleting/redownloading/deleting ...
        fudge = 1.
        # BUT only do anything if we actually made a new file!
        if nplots > 0:
            cpng = clearOldFiles(pout, "*.png", when,
                                 maxage=keephours+fudge, dtfmt=dtfmt)
            craw = clearOldFiles(dout, "*.nc", when,
                                 maxage=keephours+fudge, dtfmt=dtfmt)

            print("%d, %d raw and png files remain within %.1f + %.1f hours" %
                  (len(cpng), len(craw), keephours, fudge))

            print("Copying the latest/last files to an accessible spot...")
            # Since they're good filenames we can just sort and take the last
            #   if there are actually any current ones left of course
            nstaticfiles = 48
            if cpng != []:
                if len(cpng) < nstaticfiles:
                    lindex = len(cpng)
                else:
                    lindex = nstaticfiles

                # It's easier to do this via reverse list indicies
                icount = 0
                for findex in range(-1*lindex, 0, 1):
                    try:
                        lname = "%s/goes_latest_%03d.png" % (lout, icount)
                        icount += 1
                        copyfile(cpng[findex], lname)
                    except Exception as err:
                        # TODO: Figure out the proper/specific exception
                        print(str(err))
                        print("WHOOPSIE! COPY FAILED")

                # Put the very last file in the last file slot
                latest = cpng[-1]
                try:
                    copyfile(latest, latestname)
                    print("Latest file copy done!")
                except Exception as err:
                    # TODO: Figure out the proper/specific exception to catch
                    print(str(err))
                    print("WHOOPSIE! COPY FAILED")

            # Make the movies!
            print("Making movies...")
            movingPictures(cpng, vid1, when, videoage=vidhours, dtfmt=dtfmt)

            # 20181210 RTH: Disabling the MP4 output for now because I hates it
            # movingPictures(cpng, vid2, when, videoage=vidhours, dtfmt=dtfmt)
        else:
            print("No new files downloaded so skipping all actions.")

        print("Sleeping for %03d seconds..." % (sleep))
        time.sleep(sleep)


if __name__ == "__main__":
    outdir = "./outputs/"
    awsconf = "./awsCreds.conf"
    forceDownloads = False
    forceRegenPlot = False
    logname = './logs/goesmcgoesface.log'

    # Set up logging (using ligmos' quick 'n easy wrapper)
    logs.setup_logging(logName=logname, nLogs=30)

    creds = parseConfFile(awsconf)

    main(outdir, creds, forceDown=forceDownloads, forceRegen=forceRegenPlot)
    print("Exiting!")

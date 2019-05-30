# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 30 May 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import os
import subprocess as subp
from datetime import datetime as dt

import numpy as np

import imageio
import imageio.core.util

from PIL import Image, ImageDraw, ImageFont

import pkg_resources as pkgr

from . import utils


def movingPictures(inlist, outname, now, videoage=6., dtfmt="%Y%j%H%M%S%f"):
    """
    processing is determined by the file extension; it only knows about
    'gif' and 'mp4' at present!

    'videoage' is in hours
    """
    # Make sure 'inlist' is actually a list; needed because we index it
    inlist = list(inlist)

    maxage = videoage * 60. * 60.
    images = []
    fnames = []
    for filename in inlist:
        diff = utils.getFilenameAgeDiff(filename, now, dtfmt=dtfmt)
        if diff < maxage:
            images.append(imageio.imread(filename))
            fnames.append(filename)

    print("%d files found within %d h of now for the moving pictures" %
          (len(images), videoage))

    if len(images) < 2:
        # This means we didn't actually find any images within our window!
        #   Therefore we should just give up and go home.
        print("Not enough files found! Aborting.")
        return

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


def shift_hue(img, color=None, debug=False):
    """
    https://stackoverflow.com/questions/7274221/changing-image-hue-with-python-pil
    https://stackoverflow.com/users/190597/unutbu
    """
    # Save this for later
    origalpha = img.getchannel("A")

    # Easier to work in HSV space!
    hsv = np.array(img.convert("HSV"))

    if color is None:
        # Apply a random coloring to it to give it some ... flair
        #   This is done is HSV space, but PIL still works in 0-255.
        color = np.random.random_integers(0, high=255)

    if debug is True:
        print("Changing hue to: %d" % (color))

    # Change the color
    hsv[..., 0] = color

    # Make the color mostly saturated
    hsv[..., 1] = 200

    # Set the brightness to mostly bright
    hsv[..., 2] = 200

    # Convert back to RGB space, and slap our alpha channel back on
    rgba = Image.fromarray(hsv, mode='HSV').convert("RGBA")
    rgba.putalpha(origalpha)

    return rgba


def applyErrorLogo(img, outname, failimg=None, color=None, debug=False):
    """

    """
    if failimg is None:
        failimgloc = "resources/images/dontpanic.png"
        failimg = pkgr.resource_filename('nightshift', failimgloc)

    # Read in the images
    oimg = Image.open(img).convert("RGBA")
    fimg = Image.open(failimg).convert("RGBA")

    cimg = shift_hue(fimg, color=color, debug=debug)

    # Combine the two; this composites the second over the first
    wimg = Image.alpha_composite(oimg, cimg)
    wimg.save(outname)
    wimg.close()


def tagErrorImage(location, failimg=None, camname=None):
    """
    Given the failure image filename, add a timestamp to it
    starting at the specified pixel location (lower left corner of text).

    Leaving this hardcoded for now since it is something that's probably
    deployment dependent, but it could be abstracted with work/effort.

    Will save the resulting image to location when it's done.

    TODO: CHANGE THE HARDCODED COORDINATES IN HERE!
    """
    # This is in the package resources directory specified in the package!
    fontfile = "resources/fonts/GlacialIndifference-Bold.otf"

    ff = pkgr.resource_filename('nightshift', fontfile)
    font = ImageFont.FreeTypeFont(ff, size=24, encoding='unic')

    timestamp = dt.utcnow()
    timestring = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    if failimg is None:
        failimgloc = "resources/images/percy_txt.jpg"
        failimg = pkgr.resource_filename('nightshift', failimgloc)

    img = Image.open(failimg)
    dtxt = ImageDraw.Draw(img)

    # We don't actually need the height since I eyeballed it
    tw, _ = font.getsize(timestring)
    ntw = 170 - tw//2

    dtxt.text((ntw, 200), timestring, fill=(255, 76, 76), font=font)

    if camname is not None:
        # Same as above
        tw, _ = font.getsize(camname)
        ntw = 170 - tw//2
        dtxt.text((ntw, 85), camname, fill=(255, 76, 76), font=font)

    img.save(location)

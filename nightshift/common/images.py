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

from datetime import datetime as dt

import numpy as np
import pkg_resources as pkgr
from PIL import Image, ImageDraw, ImageFont


def resizeImage(infile, outfile, size):
    """
    """
    oimg = Image.open(infile)
    timg = oimg.resize(size, resample=Image.LANCZOS)
    timg.save(outfile)
    timg.close()
    oimg.close()


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
        color = np.random.randint(0, high=255+1)

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

    # Reduce the opacity a little bit. This is annoying to do any other way.
    nalpha = np.array(origalpha)/1.75
    nalpha = Image.fromarray(nalpha).convert("L")
    rgba.putalpha(nalpha)

    return rgba


def applyErrorLogo(img, outname, failimg=None, color=None, debug=False):
    """

    """
    if failimg is None:
        failimgloc = "resources/images/dontpanic_smaller.png"
        failimg = pkgr.resource_filename('nightshift', failimgloc)

    # Read in the images
    oimg = Image.open(img).convert("RGBA")
    fimg = Image.open(failimg).convert("RGBA")

    cimg = shift_hue(fimg, color=color, debug=debug)

    # Combine the two; this composites the second over the first
    #   NOTE: You'll get a ValueError if the size of the error stamp
    #         does not match the size of the actual base image!
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

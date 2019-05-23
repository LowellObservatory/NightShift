# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 24 Oct 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import time
import shutil
from datetime import datetime as dt

from PIL import Image, ImageDraw, ImageFont

from requests import get as httpget
from requests.exceptions import ConnectionError as RCE
from requests.auth import HTTPBasicAuth, HTTPDigestAuth


class Webcam():
    """
    Class to contain all the important bits of webcam connection information
    """
    def __init__(self):
        """
        Usual init function; doesn't allow setting via **kwargs though
        """
        self.name = None
        self.url = None
        self.user = None
        self.pasw = None
        self.auth = None
        self.floc = None
        self.enabled = False

    def assignConf(self, conf):
        """
        Accepts a ConfigParser instance and sets the __init__ params
        """
        # Assign the conf. file section title as the webcam name
        self.name = conf.name

        # Fill in the rest of the conf. file keys
        for key in conf.keys():
            if key.lower() == 'enabled':
                setattr(self, key, conf.getboolean(key))
            else:
                setattr(self, key, conf[key])


def camGrabbie(cam):
    """
    Grab an image from an individual camera as defined by the Webcam class
    """
    if cam.auth.lower() == 'digest':
        auth = HTTPDigestAuth(cam.user, cam.pasw)
    else:
        auth = HTTPBasicAuth(cam.user, cam.pasw)

    # NOTE: This'll barf if the directory (cam.floc) doesn't exist.
    #   Make sure to do that check in your calling code!
    print("Attempting to write image to %s" % (cam.floc))
    with open(cam.floc, "wb") as f:
        img = httpget(cam.url, auth=auth)
        # Check the HTTP response;
        #   200 - 400 == True
        #   400 - 600 == False
        #   Other way to do it might be to check if img.status_code == 200
        # NOTE: I needed to add this check because one webcam went
        #   *mostly dead* and returned HTTP codes and pings, but not images.
        if img.ok is True:
            print("Good grab!")
            f.write(img.content)
        else:
            # This will be caught elsewhere
            print("Bad grab :(")
            raise RCE


def tagErrorImage(failimg, location, camname=None):
    """
    Given the failure image filename, add a timestamp to it
    starting at the specified pixel location (lower left corner of text).

    Leaving this hardcoded for now since it is something that's probably
    deployment dependent, but it could be abstracted with work/effort.

    Will save the resulting image to location when it's done.
    """
    font = ImageFont.FreeTypeFont('./fonts/GlacialIndifference-Bold.otf',
                                  size=24, encoding='unic')

    timestamp = dt.utcnow()
    timestring = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

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


def grabSet(camset, failimg, interval=0.5):
    """
    Grab all camera images
    """
    for cam in camset:
        currentCamera = camset[cam]
        print('Retrieving camera image: %s' % (currentCamera.name))

        try:
            camGrabbie(currentCamera)
        except RCE as err:
            print(str(err))
            tagErrorImage(failimg, currentCamera.floc,
                          camname=currentCamera.name)
            # shutil.copy(failimg, currentCamera.floc)

        time.sleep(interval)


def simpleImageCopy(url, location, failimg):
    """
    Download the file from the given URL to the given location.
    If that fails, copy the specified failure image to the location instead.
    """

    if url is None:
        failed = True
    else:
        failed = False

    # NOTE: This'll barf if the directory (cam.floc) doesn't exist.
    #   Make sure to do that check in your calling code!
    print("Attempting to write image to %s" % (location))
    with open(location, "wb") as f:
        if failed is False:
            try:
                print('Retrieving image from: %s' % (url))
                img = httpget(url)
                f.write(img.content)
            except RCE as err:
                print(str(err))
                failed = True
        else:
            print("Failed to find the latest image!")
            shutil.copy(failimg, location)

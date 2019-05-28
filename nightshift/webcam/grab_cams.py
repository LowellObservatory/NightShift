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

import re
import time
from datetime import datetime as dt

import pkg_resources as pkgr

from bs4 import BeautifulSoup

from PIL import Image, ImageDraw, ImageFont

from requests import get as httpget
from requests.exceptions import ConnectionError as RCE
from requests.auth import HTTPBasicAuth, HTTPDigestAuth


class Webcam():
    """
    Class to contain all the important bits of webcam connection information
    """
    def __init__(self):
        self.name = None
        self.url = None
        self.user = None
        self.pasw = None
        self.auth = None
        self.floc = None
        self.enabled = False


def grabSet(camset, failimg=None, interval=0.5):
    """
    Grab all camera images in the given dictionary
    """
    for cam in camset:
        currentCamera = camset[cam]
        print('Retrieving camera image: %s' % (currentCamera.name))

        outfile = "%s/%s" % (currentCamera.odir, currentCamera.oname)
        try:
            if currentCamera.type.lower() == 'webcam':
                camGrabbie(currentCamera, outfile)
            elif currentCamera.type.lower() == 'opendir':
                grabFromOpenDirectory(currentCamera, outfile)
        except RCE as err:
            # This handles the connection error cases from the specific
            #   image grabbing utility functions. They should just
            #   raise RCE directly when/if needed
            print(str(err))

            tagErrorImage(outfile, failimg=failimg,
                          camname=currentCamera.name)

        time.sleep(interval)


def camGrabbie(cam, outfile):
    """
    Grab an image from an individual camera as defined by the Webcam class
    """
    if cam.auth.lower() == 'digest':
        auth = HTTPDigestAuth(cam.user, cam.pasw)
    else:
        auth = HTTPBasicAuth(cam.user, cam.pasw)

    # NOTE: This'll barf if the directory (cam.floc) doesn't exist.
    #   Make sure to do that check in your calling code!
    print("Attempting to write image to %s" % (outfile))
    with open(outfile, "wb") as f:
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


def tagErrorImage(location, failimg=None, camname=None):
    """
    Given the failure image filename, add a timestamp to it
    starting at the specified pixel location (lower left corner of text).

    Leaving this hardcoded for now since it is something that's probably
    deployment dependent, but it could be abstracted with work/effort.

    Will save the resulting image to location when it's done.
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


def simpleImageCopy(url, location):
    """
    Download the file from the given URL to the given location.
       NOTE: The download failure condition will be handled elsewhere.
    """

    if url is None:
        raise RCE

    # NOTE: This'll barf if the directory (cam.floc) doesn't exist.
    #   Make sure to do that check in your calling code!
    print("Attempting to write image to %s" % (location))
    with open(location, "wb") as f:
        print('Retrieving image from: %s' % (url))
        img = httpget(url)
        f.write(img.content)


def getLastFileURL(url, fmask):
    """
    Assumes that the urls as returned by listFD are actually well named and
    just sorted() on the list will return a time-ordered list going from
    youngest to oldest.

    Not guaranteed, so beware.
    """
    flist = sorted(listFD(url, fmask))
    lastFile = flist[-1]

    return lastFile


def listFD(url, fmask):
    try:
        page = httpget(url, timeout=10.).text
    except Exception as err:
        # Can't find what exception the timeout raises, so catch everything
        #   for now and then go back in and put the correct one into there.
        print(str(err))
        page = None
        urls = None

    # fmask in the .conf file should be a vaild python RE specification!!
    searcher = re.compile(fmask)

    if page is not None:
        soup = BeautifulSoup(page, 'html.parser')
        urls = []
        for node in soup.find_all('a'):
            nodehref = node.get('href')
            # Now filter based on our given filemask
            #   Easiest to use just a regular expression
            searchresult = searcher.match(nodehref)
            if searchresult is not None:
                urls.append(url + '/' + node.get('href'))

    return urls


def grabFromOpenDirectory(curcam, outfile):
    """
    """
    imgURL = None
    try:
        imgURL = getLastFileURL(curcam.url, curcam.fmas)
    except IndexError as err:
        print(str(err))

    if imgURL is not None:
        simpleImageCopy(imgURL, outfile)

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

from bs4 import BeautifulSoup

from requests import get as httpget
from requests.exceptions import ConnectionError as RCE
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from ..common import images


class Webcam():
    """
    Class to contain all the important bits of webcam connection information
    """
    def __init__(self):
        self.name = None
        self.type = None
        self.url = None
        self.user = None
        self.pasw = None
        self.fmas = None
        self.auth = None
        self.odir = None
        self.oname = None
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

            images.tagErrorImage(outfile, failimg=failimg,
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
        img = httpget(cam.url, auth=auth, timeout=5.)
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
    retList = listFD(url, fmask)
    lastFile = None
    if retList is not None:
        flist = sorted(retList)
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
    else:
        # TODO: Finish this!
        pass

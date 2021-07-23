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

import os
import re
import time
import shutil
from datetime import datetime as dt

import cv2
from PIL import Image
from bs4 import BeautifulSoup

from requests import get as httpget
from requests.exceptions import ConnectionError as RCE
from requests.exceptions import ReadTimeout as RTO
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from ligmos.utils import files

from ..common import images


def grabSet(camset, failimg=None, interval=0.5, archive=False,
            makeMini=True, cullArchive=True):
    """
    Grab all camera images in the given dictionary
    """
    # This is the size that NightWatch uses
    thumbSize = [400, 235]

    # Oldest date to keep in the archive is this many days old
    oldArchiveAge = 30

    for cam in camset:
        currentCamera = camset[cam]
        print('Retrieving camera image: %s' % (cam))

        # Hack to save both the latest and the previous ones
        nowTime = dt.utcnow()
        nowTimeStr = nowTime.strftime("%Y%m%d_%H%M%S")
        nowDateStr = nowTime.strftime("%Y%m%d")

        # This is the static (current/most recent) image
        outfile = "%s/%s" % (currentCamera.odir, currentCamera.oname)

        # This is the same but the smaller thumbnail version
        thumbfile = "%s/thumb_%s" % (currentCamera.odir, currentCamera.oname)
        try:
            if currentCamera.type.lower() == 'webcam':
                camGrabbie(currentCamera, outfile)
            elif currentCamera.type.lower() == 'opendir':
                grabFromOpenDirectory(currentCamera, outfile)
            elif currentCamera.type.lower() == 'rtsp':
                grabFromRTSP(currentCamera, outfile)

            # Only worth archiving images that are real!  If any of the above
            #   functions raise RCE this will get skipped which I think is fine
            if archive is True:
                curOutName = currentCamera.oname.split(".")
                archiveBase = "%s/archive/%s/" % (currentCamera.odir,
                                                  curOutName[0])

                # Make sure the archive root exists already
                _ = files.checkOutDir(archiveBase, getList=True)

                # Actually archive the new files
                thisarchivedir = "%s/%s/" % (archiveBase, nowDateStr)
                files.checkOutDir(thisarchivedir, getList=False)
                archivefile = "%s/%s.%s" % (thisarchivedir,
                                            nowTimeStr, curOutName[1])

                print("File will be archived as: %s" % (archivefile))
                # Now copy the file to the archive location
                #      copy(src, dest)
                try:
                    shutil.copy(outfile, archivefile)
                except Exception as e:
                    print(str(e))

                # Perform the archive culling; this will preserve the last
                #   ones in the archive if a camera goes offline for a while
                #   and isn't noticed, so I'll be able to track down when it
                #   was last seen.  Seems like a good idea.
                if cullArchive is True:
                    _, oldDirs = files.findOldFiles(archiveBase, "*", nowTime,
                                                    maxage=oldArchiveAge*24.,
                                                    dtfmt="%Y%m%d")
                    if oldDirs != {}:
                        files.deleteOldDirectories(oldDirs)

            if cam.extracopy is not None:
                if cam.extracopy_prefix is not None:
                    extrafile = "%s/%s_%s.%s" % (cam.extracopy,
                                                 cam.extracopy_prefix,
                                                 nowTimeStr, curOutName[1])
                else:
                    extrafile = "%s/%s.%s" % (cam.extracopy,
                                              nowTimeStr, curOutName[1])
                try:
                    print("Doing extra copy to %s" % (cam.extrafile))
                    shutil.copy(outfile, extrafile)
                except Exception as e:
                    print(str(e))
        except RCE as err:
            # This handles the connection error cases from the specific
            #   image grabbing utility functions. They should just
            #   raise RCE directly when/if needed
            print(str(err))

            images.tagErrorImage(outfile, failimg=failimg,
                                 camname=cam)

        # We always want to make a thumbnail sized image of the latest thing
        if makeMini is True:
            print("Making thumbnail sized image...")
            # Make a thumbnail-sized version I can easily include elsewhere
            images.resizeImage(outfile, thumbfile, thumbSize)

        time.sleep(interval)


def camGrabbie(cam, outfile):
    """
    Grab an image from an individual camera as defined by the Webcam class
    """
    if cam.auth.lower() == 'digest':
        auth = HTTPDigestAuth(cam.user, cam.password)
    else:
        auth = HTTPBasicAuth(cam.user, cam.password)

    # NOTE: This'll barf if the directory (cam.floc) doesn't exist.
    #   Make sure to do that check in your calling code!
    print("Attempting to write image to %s" % (outfile))
    with open(outfile, "wb") as f:
        try:
            img = httpget(cam.url, auth=auth, timeout=5.)
            # Check the HTTP response;
            #   200 - 400 == True
            #   400 - 600 == False
            #   Other way to do it might be to check if img.status_code == 200
            # NOTE: I needed to add this check because one webcam went
            #   *mostly dead* and returned HTTP codes and pings, but not images
            if img.ok is True:
                f.write(img.content)
                print("Good grab and write to disk as %s!" % (outfile))
            else:
                # This will be caught elsewhere
                print("Bad grab :(")
                raise RCE
        except RTO as err:
            print("Bad grab :(")
            print(str(err))
            raise RCE

    # Test to make sure the image wasn't 0 bytes!
    #   Can happen if the request succeeds but the camera is
    #   being weird and mid-boot or some other intermittent quirk
    imgSize = os.stat(outfile).st_size
    if imgSize == 0:
        print("Saved image was 0 bytes - it was really a bad grab :(")
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

    # Test to make sure the image wasn't 0 bytes!
    #   Can happen if the request succeeds but the camera is
    #   being weird and mid-boot or some other intermittent quirk
    imgSize = os.stat(location).st_size
    if imgSize == 0:
        print("Saved image was 0 bytes - it was really a bad grab :(")
        raise RCE


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


def grabFromRTSP(curcam, outfile):
    """
    Assumes that curcam.url includes the RTSP endpoint.  Doesn't provide
    a way to change the RTSP port, so make sure that's in the URL too.
    If those aren't the case, this needs to be changed!
    """
    urlparts = curcam.url.lower().split("://")
    urlprefix = None
    if len(urlparts) == 1:
        # This implies it was just an ip or a hostname
        urlprefix = "rtsp"

    if urlparts[0] in ['http', 'https', None]:
        print("Invalid URL! Skipping.")
        return
    elif urlprefix == 'rtsp' or urlprefix is None:
        # Insert the username and password inline if we have it
        if curcam.user is not None and curcam.password is not None:
            newurl = "rtsp://%s:%s@%s" % (curcam.user, curcam.password,
                                          urlparts[1])
        else:
            newurl = "rtsp://%s" % (urlparts[1])

        try:
            snap = None
            success = False
            client = cv2.VideoCapture(newurl)
            # Check to make sure the client opened otherwise we can get
            #   a very cryptic segfault-ish crash
            if client.isOpened() is True:
                print("RTSP Opened...")
                (success, snap) = client.read()
                if success is True:
                    print("Frame grabbed!")
                client.release()
                print("RTSP Closed")

            if snap is not None and success is True:
                saveme = Image.fromarray(cv2.cvtColor(snap, cv2.COLOR_BGR2RGB))
                print("Saving to %s" % (outfile))
                saveme.save(outfile)
            else:
                # Should I really do this?  I think so, this will trigger
                #   the creation of the error image
                raise RCE
        except Exception as e:
            # TODO: Catch the specific exceptions possible here
            print(str(e))

            raise RCE from e

    # Test to make sure the image wasn't 0 bytes!
    #   Can happen if the request succeeds but the camera is
    #   being weird and mid-boot or some other intermittent quirk
    imgSize = os.stat(outfile).st_size
    if imgSize == 0:
        print("Saved image was 0 bytes - it was really a bad grab :(")
        raise RCE

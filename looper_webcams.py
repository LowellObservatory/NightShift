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

from ligmos.utils import logs, files, classes, confparsers

from nightshift.webcam import grab_cams as cams


def main():
    """
    """
    # Switch to file-based logging since docker logs -f is mysteriously failing
    lfile = './outputs/logs/camLooper.log'
    cfile = './config/webcams.conf'
    pfile = './config/passwords.conf'
    confclass = classes.Webcam

    # Need to pass getList = False otherwise it'll try to generate a list
    #   of files found in that directory and return it to you.
    files.checkOutDir('./outputs/logs/', getList=False)

    # If abort was True, this'll probably blow up...?
    logs.setup_logging(logName=lfile, nLogs=5)

    # Read the webcam config file and parse it accordingly.
    #   Will return an OrderedDict of enabled webcams IF enableCheck is True
    oncams, _ = confparsers.parseConfig(cfile, confclass,
                                        passfile=pfile,
                                        searchCommon=False,
                                        enableCheck=True)

    # Before we start, check the ALL the image output directories.
    #   Only checking the enabled ones, but could check allcams if desired.
    for cam in oncams:
        curcam = oncams[cam]

        # Test the output location to make sure it exists
        location = curcam.odir
        files.checkOutDir(location, getList=False)

    # Just run it for ever and ever and ever and ever and ever and ever
    while True:
        # failimg = None just uses the default one:
        #   resources/images/percy_txt.jpg
        # Note: Archive locations will be created automatically in here
        cams.grabSet(oncams, failimg=None, makeMini=True)
        print("Done Grabbing Images!")

        print("Sleeping for 60 seconds...")
        time.sleep(60.)


if __name__ == "__main__":
    main()

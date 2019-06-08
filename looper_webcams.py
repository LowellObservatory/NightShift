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

from collections import OrderedDict

import time

from ligmos.utils import confparsers, confutils, files, logs

from nightshift.common import utils as comutils
from nightshift.webcam import grab_cams as cams


def webcamConf(config):
    """
    Simple function to return two dictionaries:

    allcams will contain all the entries in the .conf file
    oncams will contain only those in which enabled=True
    """
    # Ultimate storage locations of final results
    #   allcams will contain everything
    #   oncams will contain only those with enabled == True
    allcams = OrderedDict()
    oncams = OrderedDict()

    for each in config.keys():
        print("Applying '%s' section of conf. file..." % (each))
        wcam = cams.Webcam()

        # Stuff the actual values into the properties, as named in the
        #   actual .conf file; no error checking is done to see if those
        #   defined in the class are actually those being assigned,
        #   so there could still be problems lurking.
        wcam = confutils.assignConf(wcam, config[each])

        # Stuff the name in so the next part isn't so awkward
        wcam.name = each

        allcams.update({wcam.name: wcam})

        if wcam.enabled is True:
            oncams.update({wcam.name: wcam})

    print("%d endpoints defined, %d enabled" % (len(allcams), len(oncams)))

    return allcams, oncams


def main():
    """
    """
    # Switch to file-based logging since docker logs -f is mysteriously failing
    lfile = './outputs/logs/camLooper.log'
    cfile = './config/webcams.conf'

    # Need to pass getList = False otherwise it'll try to generate a list
    #   of files found in that directory and return it to you.
    files.checkOutDir('./outputs/logs/', getList=False)

    # If abort was True, this'll probably blow up...?
    logs.setup_logging(logName=lfile, nLogs=5)

    # Read the webcam config file and parse it accordingly.
    #   Will return an OrderedDict of enabled webcams IF enableCheck is True
    basecamConfig, _ = confparsers.parseConfFile(cfile,
                                                 commonBlocks=False,
                                                 enableCheck=True)
    allcams, oncams = webcamConf(basecamConfig)

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
        cams.grabSet(oncams, failimg=None)
        print("Done Grabbing Images!")

        print("Sleeping for 60 seconds...")
        time.sleep(60.)


if __name__ == "__main__":
    main()

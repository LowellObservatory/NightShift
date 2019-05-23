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

import os
import time
import configparser as conf

from ligmos import utils

import grab_cams as cams


def parseConfFile(filename):
    """
    Parse the .conf file that gives the setup per webcam.
    Returns an ordered dict of Webcam classes in which
    'enabled=True' is in the section.
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


def webcamConf(config):
    # Ultimate storage locations of final results
    #   allcams will contain everything
    #   oncams will contain only those with enabled == True
    allcams = OrderedDict()
    oncams = OrderedDict()

    for each in config.sections():
        print("Applying '%s' section of conf. file..." % (each))
        wcam = cams.Webcam()
        wcam.assignConf(config[each])

        allcams.update({wcam.name: wcam})

        if wcam.enabled is True:
            oncams.update({wcam.name: wcam})

    print()

    return allcams, oncams


def checkDir(location):
    """
    Check the given path for existance, and create it if needed.

    I admit there's a possibility for a race condition between the check for
    existance and the actual creation.  Shouldn't matter for most of what
    I need this for, though, so I'm running with this for now.
    """

    outdir = os.path.abspath(os.path.dirname(location))
    print("Checking output location: %s" % (outdir))

    dirExists = os.path.isdir(outdir)

    abort = False
    if dirExists is False:
        try:
            print("Directory didn't exist! Creating it...")
            os.makedirs(outdir)
            print("Done!")
        except OSError as err:
            # Something bad happened. Could be a race condition between
            #   the check for dirExists and the actual creation of the
            #   directory/tree, but scream and signal an abort.
            print(str(err))
            abort = True
    else:
        print("Directory existed! Moving on.")

    return abort


def main():
    # Switch to file-based logging since docker logs -f is mysteriously failing
    lfile = './logs/camLooper.log'
    abort = checkDir('./logs/')
    # If abort was True, this'll probably blow up...?
    utils.logs.setup_logging(logName=lfile, nLogs=5)

    # Default image to show when webcams are offline
    failImg = "./errimages/percy_txt.jpg"

    # Read the webcam config file and parse it accordingly.
    #   Will return an OrderedDict of enabled webcams.
    basecamConfig = parseConfFile('./webcams.conf')
    allcams, oncams = webcamConf(basecamConfig)

    # Before we start, check the output directories.
    #   Only checking the enabled ones, but could check allcams if desired.
    for cam in oncams:
        curcam = oncams[cam]

        # Test the output location to make sure it exists
        location = curcam.floc
        abort = checkDir(location)
        # Bail on the first problem
        if abort is True:
            break

    # Just run it for ever and ever and ever and ever and ever and ever
    if abort is False:
        while True:
            cams.grabSet(oncams, failImg)
            print("Done Grabbing Images!")

            print("Sleeping for 60 seconds...")
            time.sleep(60.)
    else:
        print("ABORTING! Can't create output directory")


if __name__ == "__main__":
    main()

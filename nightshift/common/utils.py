# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 22 May 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import os
import glob
from shutil import copyfile
import configparser as conf
from collections import OrderedDict
from datetime import datetime as dt


def parseConfFile(filename, enableCheck=True):
    """
    TODO: Check to see if this is duplicated in ligmos
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

    if enableCheck is True:
        enconfig = checkEnabled(config)
    else:
        enconfig = dict(config)

    return enconfig


def checkEnabled(conf):
    """
    TODO: Check to see if this is duplicated in ligmos
    TODO: Check to see if this can be combined with assignConf
    """
    enset = OrderedDict()
    for sect in conf.sections():
        en = False
        for key in conf[sect].keys():
            if key.lower() == 'enabled':
                en = conf[sect].getboolean(key)
                if en is True:
                    enset.update({sect: conf[sect]})

    return enset


def assignConf(classInstance, conf):
    """
    Accepts a ConfigParser instance and sets the parameters found within it
    TODO: Check to see if this is duplicated in ligmos
    TODO: Check to see if this can be combined with checkEnabled
    """
    # Assign the conf. file section title as the webcam name
    classInstance.name = conf.name

    # Fill in the rest of the conf. file keys
    for key in conf.keys():
        if key.lower() == 'enabled':
            setattr(classInstance, key, conf.getboolean(key))
        else:
            setattr(classInstance, key, conf[key])

    return classInstance


def getFilenameAgeDiff(fname, now, dtfmt="%Y%j%H%M%S%f"):
    """
    NOTE: HERE 'maxage' is already in seconds! Convert before calling.
    """
    # Need to basename it to get just the actual filename and not the path
    beach = os.path.basename(fname)

    # Match the basename-ed filename length to our dtfmt string
    #   This is so we don't have to worry about 'unconverted data remains'
    #   errors from strptime below
    beach = beach[:len(dtfmt)]

    try:
        dts = dt.strptime(beach, dtfmt)
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


def copyStaticFilenames(nstaticfiles, lout, staticname, cpng):
    """
    """
    latestname = '%s/%s_latest.png' % (lout, staticname)

    if cpng != []:
        if len(cpng) < nstaticfiles:
            lindex = len(cpng)
        else:
            lindex = nstaticfiles

        # It's easier to do this via reverse list indicies
        icount = 0
        for findex in range(-1*lindex, 0, 1):
            try:
                lname = "%s/%s_%03d.png" % (lout, staticname, icount)
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


def checkOutDir(outdir, getList=True):
    """
    """
    # Check if the directory exists, and if not, create it!
    try:
        os.makedirs(outdir)
    except FileExistsError:
        pass
    except OSError as err:
        # Something bad happened. Could be a race condition between
        #   the check for dirExists and the actual creation of the
        #   directory/tree, but scream and signal an abort.
        print(str(err))
    except Exception as err:
        # Catch for other (permission?) errors just to be safe for now
        print(str(err))

    flist = None
    if getList is True:
        flist = sorted(glob.glob(outdir + "/*"))
        flist = [os.path.basename(each) for each in flist]

    return flist

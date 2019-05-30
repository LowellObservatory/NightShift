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

from . import images


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

    try:
        dts = dt.strptime(beach, dtfmt)
        diff = (now - dts).total_seconds()
    except Exception as err:
        # TODO: Catch the right datetime conversion error!
        print(str(err))
        # Make it "current" to not delete it
        diff = 0

    return diff


def deleteOldFiles(fdict):
    """
    fdict should be a dictionary whose key is the filename and the
    value is that filename's determined age (in seconds)
    """
    for key in fdict:
        print("Deleting %s since it's too old (%.3f hr)" %
              (key, fdict[key]/60./60.))
        try:
            os.remove(key)
        except OSError as err:
            # At least see what the issue was
            print(str(err))


def findOldFiles(inloc, fmask, now, maxage=24., dtfmt="%Y%j%H%M%S%f"):
    """
    'maxage' is in hours

    Returns two dictionaries, one for the current (young) files and one
    for the out-of-date (old) files. Both dicts are set up the same,
    with the keys being the filenames and their values their determined age.
    """
    maxage *= 60. * 60.
    flist = sorted(glob.glob(inloc + fmask))

    goldenoldies = {}
    youngsters = {}
    for each in flist:
        diff = getFilenameAgeDiff(each, now, dtfmt=dtfmt)
        if diff > maxage:
            goldenoldies.update({each: diff})
        else:
            youngsters.update({each: diff})

    return youngsters, goldenoldies


def copyStaticFilenames(cpng, lout, staticname, nstaticfiles,
                        errorAge=4., errorStamp=False):
    """
    cpng should be a dict, whose key is the filename and the
    value is that filename's determined age (in seconds)

    errorAge is given in hours and then converted to seconds
    """
    latestname = '%s/%s_latest.png' % (lout, staticname)

    errorAge *= 60. * 60.

    # Since we gave it a dict we just put it into a list to make
    #   indexing below a little easier.
    clist = list(cpng.keys())
    cages = list(cpng.values())

    # Make sure we don't try to operate on an empty dict, or one too small
    if len(cpng) < nstaticfiles:
        lindex = len(cpng)
    else:
        lindex = nstaticfiles

    icount = 0
    # It's easier to do this in reverse
    for findex in range(-1*lindex, 0, 1):
        try:
            lname = "%s/%s_%03d.png" % (lout, staticname, icount)
            icount += 1
            if errorStamp is True:
                # Check to see if our file's age is too old, and if so,
                #   apply the error stamp
                if cages[findex] >= errorAge:
                    images.applyErrorLogo(clist[findex], lname)
                else:
                    copyfile(clist[findex], lname)
            else:
                copyfile(clist[findex], lname)
        except Exception as err:
            # TODO: Figure out the proper/specific exception
            print(str(err))
            print("WHOOPSIE! COPY FAILED")

    # Put the very last file in the last file slot
    latest = clist[-1]
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

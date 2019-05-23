# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 15 Nov 2018
#
#  @author: rhamilton

"""Grab GOES16 data from AWS bucket(s)

Requires AWS credentials in the awsCreds.conf file.
"""

from __future__ import division, print_function, absolute_import

from os.path import basename
from datetime import timedelta as td

import boto3
import botocore
import numpy as np

from .. import common as com


def NEXRADAWSgrab(aws_keyid, aws_secretkey, now, outdir,
                  timedelta=6, forceDown=False):
    """
    AWS IAM user key
    AWS IAM user secret key
    Time query is relative to (usually datetime.datetime.utcnow)
    Hours to query back from above
    """
    # AWS GOES bucket location/name
    awsbucket = 'noaa-nexrad-level2'
    awszone = 'us-east-1'

    # Station ID that you want to download
    station = "KFSX"

    # Check our output directory for files already downloaded
    donelist = com.utils.checkOutDir(outdir)

    # Sample key:
    # 2019/05/17/KFSX/KFSX20190517_000556_V06

    # Construct the key prefixes between the oldest and the newest
    querybins = []
    minmaxhour = []

    # timedelta MUST be an int...
    timedelta = np.int(np.round(timedelta, decimals=0))

    # Construct the query keys; this will get us to the relevant bits
    #   in the AWS bucket,
    for i in range(timedelta, -1, -1):
        delta = td(hours=i)
        qdt = (now - delta).timetuple()

        # Include the year so it works on 1/1 UT
        qyear = qdt.tm_year
        qmonth = qdt.tm_mon
        qday = qdt.tm_mday
        qhour = qdt.tm_hour

        ckey = "%04d/%02d/%02d/%s" % (qyear, qmonth, qday, station)
        # Since we're hacking against the GOES version, lets just skip things
        #   if we just keep making the same string; GOES bucket was organized
        #   by hour, so that made more sense back then
        # (check against i==timedelta because we loop backwards)
        if i == timedelta:
            querybins.append(ckey)
            minmaxhour.append(qhour)
        else:
            if ckey != querybins[-1]:
                querybins.append(ckey)

    minmaxhour.append(qhour)

    s3 = boto3.resource('s3', awszone,
                        aws_access_key_id=aws_keyid,
                        aws_secret_access_key=aws_secretkey)

    try:
        buck = s3.Bucket(awsbucket)
    except botocore.exceptions.ClientError as e:
        # NOTE: Is this the correct exception?  No clue.
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

    matches = []
    # Bit of a hack; for the first querybin, there's a hour limit that
    #   we won't want any data before because it'll be outside of our
    #   requested time range.  Ditto for the last bin, but it'll be
    #   that we don't want any data past that point.  In between,
    #   we assume that we want absolutely everything so there is no limit.
    minHour = minmaxhour[0]
    maxHour = minmaxhour[1]

    for i, qt in enumerate(querybins):
        if i == 0:
            cutOff = "min"
        elif i == len(qt):
            cutOff = "max"
        else:
            cutOff = None

        print("Querying:", qt)
        try:
            todaydata = buck.objects.filter(Prefix=qt)

            for objs in todaydata:
                # Current filename
                ckey = basename(objs.key)

                # print("Found %s" % (ckey))

                # Specific filename to search for. Pretty simple since
                #   there aren't many variations, just the occasional
                #   '_MDM' file that we will ignore
                qtp = qt.split('/')
                fkey = "%s%s%s%s" % (qtp[3], qtp[0], qtp[1], qtp[2])

                # Bit of hackey magic. Sorry.
                keyhour = int(ckey.split("_")[1][0:2])

                skipFile = True
                if cutOff == "min":
                    if keyhour < minHour:
                        skipFile = True
                        print("Skipping file %s, too old!" % (ckey))
                    else:
                        skipFile = False
                elif cutOff == "max":
                    if keyhour > maxHour:
                        skipFile = True
                        print("Skipping file %s, too new!" % (ckey))
                    else:
                        skipFile = False
                else:
                    skipFile = False

                # Skip the "_MDM" file, whatever it is
                if len(ckey.split("_")) == 4:
                    if ckey.split("_")[3] == "MDM":
                        skipFile = True
                        print("Skipping file %s, it's an MDM!" % (ckey))

                # Now only select ones that match our product and our channel
                if ckey.startswith(fkey) and skipFile is False:
                    # Construct the output filename to save it as
                    oname = "_".join(ckey.split("_")[0:2])
                    oname = "%s/%s" % (outdir, oname)

                    # Just basename it so we can quickly check to see if
                    #   we already downloaded this file; if so, skip it.
                    boname = basename(oname)
                    if boname not in donelist:
                        matches.append(objs)
                        try:
                            buck.download_file(objs.key, oname)
                            print("Downloaded: %s" % (oname))
                        except botocore.exceptions.ReadTimeoutError:
                            print("DOWNLOAD FAILURE! ReadTimeoutError")
                        except ConnectionError:
                            print("DOWNLOAD FAILURE!")
                            print("ConnectionError or subclass of it.")
                    else:
                        print(oname, "already downloaded!")
                        if forceDown is True:
                            print("Download forced.")
                            buck.download_file(objs.key, oname)

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
            else:
                raise
        except botocore.exceptions.EndpointConnectionError:
            print("QUERY FAILURE! EndpointConnectionError")

    return matches

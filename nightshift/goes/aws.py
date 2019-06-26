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

import botocore
import numpy as np

from ligmos.utils import files

from .. import common as com


def genQueries(timedelta, now, inst):
    """
    """
    # Sample key:
    # ABI-L2-CMIPC/2018/319/23/OR_ABI-L2-CMIPC-M3C13_G16_ +
    #                          s20183192332157_e20183192334541_ +
    #                          c20183192334582.nc

    # Construct the key prefixes between the oldest and the newest
    querybins = []

    # timedelta MUST be an int...
    timedelta = np.int(np.round(timedelta, decimals=0))

    for i in range(timedelta, -1, -1):
        delta = td(hours=i)
        qdt = (now - delta).timetuple()

        # Include the year so it works on 1/1 UT
        qyear = qdt.tm_year
        qday = qdt.tm_yday
        qhour = qdt.tm_hour

        ckey = "%s/%04d/%03d/%02d/" % (inst, qyear, qday, qhour)
        querybins.append(ckey)
    # print(querybins)

    return querybins


def GOESAWSgrab(aws_keyid, aws_secretkey, now, outdir,
                timedelta=6, forceDown=False):
    """
    AWS IAM user key
    AWS IAM user secret key
    Time query is relative to (usually datetime.datetime.utcnow)
    Hours to query back from above
    """
    # AWS GOES bucket location/name
    #  https://registry.opendata.aws/noaa-goes/
    awsbucket = 'noaa-goes16'
    awszone = 'us-east-1'

    # ABI: Advanced Baseline Imager
    # L2: "Level 2" (processed) data
    # CMIPC are the "Cloud & Moisture Imagery CONUS" products
    #   these are derived products based on the "ABI-L1b-Rad*" data
    #   See also: https://www.ncdc.noaa.gov/data-access/satellite-data/goes-r-series-satellites
    inst = "ABI-L2-CMIPC"
    channel = 13

    # Check our output directory for files already downloaded
    donelist = files.checkOutDir(outdir)

    querybins = genQueries(timedelta, now, inst)

    # Establish the connection to the S3 bucket
    buck = com.aws.connectS3(awsbucket, awszone, aws_keyid, aws_secretkey)

    matches = []
    for qt in querybins:
        print("Querying:", qt)
        try:
            todaydata = buck.objects.filter(Prefix=qt)

            for objs in todaydata:
                # Current filename
                ckey = basename(objs.key)

                # print("Found %s" % (ckey))

                # Specific filename to search for. Do it in two parts,
                #   one here to select the instrument/product and another
                #   to select the desired channel
                # Backup of original query:
                # fkey = "OR_%s-M3C%02d_G16" % (inst, channel)
                fkey = "OR_%s-M" % (inst)
                chankey = "C%02d" % (channel)

                # Bit of hackey magic. Sorry. Needed to ignore the "mode"
                #   parameter but still check the channel
                keyparts = ckey.split("_")[1].split("-")[3]

                # Now only select ones that match our product and our channel
                if ckey.startswith(fkey) and keyparts.endswith(chankey):
                    # Construct the output filename to save it as
                    oname = ckey.split("_")[4][1:]
                    oname = "%s/%s_C%02d.nc" % (outdir, oname, channel)

                    # Just basename it so we can quickly check to see if
                    #   we already downloaded this file; if so, skip it.
                    boname = basename(oname)
                    if boname not in donelist:
                        matches.append(objs)
                        # Actually attempt the download
                        com.aws.downloadFromS3(buck, objs, oname)
                    else:
                        print(oname, "already downloaded!")
                        if forceDown is True:
                            print("Download forced.")
                            com.aws.downloadFromS3(buck, objs, oname)

        except botocore.exceptions.ClientError as e:
            # Needed for handling interrupted connections
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
            else:
                raise
        except botocore.exceptions.EndpointConnectionError:
            # Needed for handling interrupted connections
            print("QUERY FAILURE! EndpointConnectionError")

    return matches

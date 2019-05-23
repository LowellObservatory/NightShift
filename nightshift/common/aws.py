# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 23 May 2019
#
#  @author: rhamilton

"""Common utilities for connecting to and downloading data from AWS
"""

from __future__ import division, print_function, absolute_import

import boto3
import botocore


def connectS3(bucket, zone, keyid, secretkey):
    """
    """
    s3 = boto3.resource('s3', zone,
                        aws_access_key_id=keyid,
                        aws_secret_access_key=secretkey)
    buck = None
    try:
        buck = s3.Bucket(bucket)
    except botocore.exceptions.ClientError as e:
        # NOTE: Is this the correct exception?  No clue.
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

    return buck


def downloadFromS3(buck, objs, oname):
    """
    """
    try:
        buck.download_file(objs.key, oname)
        print("Downloaded: %s" % (oname))
    except botocore.exceptions.ReadTimeoutError:
        print("DOWNLOAD FAILURE! ReadTimeoutError")
    except ConnectionError:
        print("DOWNLOAD FAILURE!")
        print("ConnectionError or subclass of it.")

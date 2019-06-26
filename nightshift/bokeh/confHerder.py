# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 21 Dec 2018
#
#  @author: rhamilton

"""
"""

from __future__ import division, print_function, absolute_import

from collections import OrderedDict

from ligmos.utils import classes
from ligmos.utils.confparsers import parseConfig
from ligmos.workers.confUtils import assignConf, assignComm


from . import confClasses
# from ..common import utils as comutil


def groupConfFiles(queries, modules):
    """
    This is specifically for the NightWatch setup, in which we have
    distinct configuration files for the database queries and the modules
    that utilize them.
    """
    moduleDict = {}
    qDict = OrderedDict()

    for sect in modules.keys():
        mod = modules[sect]

        # Assign the query objects to the module class now
        mod.combineConfs(queries)

        # Sanity checks
        if mod.queries == {}:
            # This means we didn't find any valid queries so we'll skip
            #   the module entirely so we don't crash out
            mod = None

        # Did we survive?
        if mod is not None:
            moduleDict.update({sect: mod})

            # Loop thru the queries in this module, and check to see if
            #   we've already recorded them as being needed
            for q in mod.queries:
                if q not in qDict:
                    qDict.update({q: mod.queries[q]})

    return moduleDict, qDict


def parser(qconff, mconff, passes=None):
    """
    """
    # Parse the big list of queries
    #   We assume all the queries are live, hence enableCheck is False
    qs, cb = parseConfig(qconff, classes.databaseQuery, passfile=passes,
                         searchCommon=True, enableCheck=False)

    # Associate the database queries with the proper database connection class
    qs = assignComm(qs, cb, commkey='database')

    # Parse the text file and check if any sections are disabled
    #   No common blocks in the module config are possible so skip that
    ms, _ = parseConfig(mconff, confClasses.moduleConfig, passfile=passes,
                        searchCommon=False, enableCheck=True)

    # Now combine the modules and queries into stuff we can itterate over
    modules, queries = groupConfFiles(qs, ms)

    # 'modules' is now a list of moduleConfig objects. If any of the entries
    #   in mconff had queries that didn't match entries in qconff, that module
    #   was obliterated completely and will be ignored!
    # 'queries' is a list of all the active database sections associated
    #   with the individual modules. It's technically a set, so no dupes.
    # Now we're ready for an actual loop! But let someone else do it.

    return modules, queries

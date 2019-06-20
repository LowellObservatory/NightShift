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

from ligmos.utils.confparsers import parseConfFile
from ligmos.utils.confutils import assignConf, parseConfPasses
from ligmos.utils import classes

from . import confClasses
# from ..common import utils as comutil


def alignDBConfig(queries):
    """
    We follow a slightly different scheme here, to allow the possibility
    of multiple independent databases or tables.  That's not possible using
    the standardized layout over in ligmos, but we still use that parser
    to get started.
    """
    dbs = OrderedDict()
    vqs = OrderedDict()
    for sec in queries:
        if sec.lower().startswith("database-") or\
           sec.lower().startswith("broker-"):
            baseTarg = assignConf(classes.baseTarget(), queries[sec])
            dbs.update({sec: baseTarg})
        elif sec.lower() != 'default':
            # There's always a "DEFAULT" section after parsing so skip it
            dbq = assignConf(classes.databaseQuery(), queries[sec])
            # Setting this outside of __init__ is fine with me
            #   since we're really just renaming for convienence elsewhere
            #   (so I remember that I can ignore this in pylint)
            dbq.key = sec
            try:
                dbkey = queries[sec]['db']
                dbq.db = dbs[dbkey]
            except AttributeError:
                print("FATAL ERROR: database %s not specified!" % (dbkey))
                dbq = None
            vqs.update({sec: dbq})

    return vqs


def groupConfFiles(queries, modules):
    """
    This is specifically for the NightWatch setup, in which we have
    distinct configuration files for the database queries and the modules
    that utilize them.
    """
    moduleDict = {}
    # loopableSet = []
    allQueries = []
    for sect in modules.keys():
        # Parse the conf file section.
        mod = assignConf(confClasses.moduleConfig(), modules[sect])

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
            # loopableSet.append(mod)
            allQueries += mod.queries.values()

        # Turn the unique set of queries into something a little easier to
        #   interact and associate with later on in the codes
        qS = set(allQueries)
        qDict = OrderedDict()
        for q in qS:
            qDict.update({q.key: q})

    return moduleDict, qDict


def parser(qconff, mconff, passes=None):
    """
    """
    # Parse the big list of queries
    #   It has a common block for database info, but not in the usual sense
    #   so we need to skip our usual checks for such things
    if passes is not None:
        pass
        # This needs to be rethought. Will probably remove commonBlocks
        #   concept from parseConfFile in deference to combining
        #   in the bits from parseConfPasses that are needed!
        # qs, _ = parseConfPasses()
    else:
        qs, _ = parseConfFile(qconff, commonBlocks=False, enableCheck=False)

    # Associate the database queries with the proper database connection class
    qs = alignDBConfig(qs)

    # Parse the text file and check if any sections are disabled
    #   No common blocks in the module config are possible so skip that
    ms, _ = parseConfFile(mconff, commonBlocks=False, enableCheck=True)

    # Now combine the modules and queries into stuff we can itterate over
    modules, queries = groupConfFiles(qs, ms)

    # 'modules' is now a list of moduleConfig objects. If any of the entries
    #   in mconff had queries that didn't match entries in qconff, that module
    #   was obliterated completely and will be ignored!
    # 'queries' is a list of all the active database sections associated
    #   with the individual modules. It's technically a set, so no dupes.
    # Now we're ready for an actual loop! But let someone else do it.

    return modules, queries

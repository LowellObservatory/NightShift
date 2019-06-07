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

from ligmos.utils.confutils import assignConf
from ligmos.utils.confparsers import parseConfFile
# from ..common import utils as comutil


class moduleConfig():
    def __init__(self):
        self.title = ''
        self.queries = None
        self.drange = 1
        self.pymodule = None
        self.endpoint = None
        self.enabled = False

    def combineConfs(self, queries):
        qdict = OrderedDict()
        # Take care of single query configurations; otherwise the following
        #   loop would shred the string into its component characters and
        #   would obviously not work
        if isinstance(self.queries, str):
            self.queries = [self.queries]

        for q in self.queries:
            try:
                qdict.update({q: queries[q]})
            except KeyError:
                print("Query %s is undefined! Skipping it..." % (q))

        self.queries = qdict


class databaseConfig():
    def __init__(self):
        self.host = ''
        self.port = 8086
        self.type = 'influxdb'
        self.tabl = None
        self.user = None
        self.pasw = None


class databaseQuery():
    def __init__(self):
        self.db = None
        self.mn = None
        self.fn = None
        self.dn = None
        self.tn = None
        self.tv = None
        self.rn = 24


def alignDBConfig(queries):
    """
    """
    dbs = OrderedDict()
    vqs = OrderedDict()
    for sec in queries:
        if sec.lower().startswith("database-"):
            idb = assignConf(databaseConfig(), queries[sec])
            dbs.update({sec: idb})
        elif sec.lower() != 'default':
            dbq = assignConf(databaseQuery(), queries[sec])
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
    """
    moduleDict = {}
    # loopableSet = []
    allQueries = []
    for sect in modules.keys():
        # Parse the conf file section.
        mod = assignConf(moduleConfig(), modules[sect])

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


def parser(qconff, mconff):
    """
    """
    # Parse the text file
    qs = parseConfFile(qconff, enableCheck=False)

    # Associate the database queries with the proper database connection class
    qs = alignDBConfig(qs)

    # Parse the text file and check if any sections are disabled
    ms = parseConfFile(mconff, enableCheck=True)

    # Now combine the modules and queries into stuff we can itterate over
    modules, queries = groupConfFiles(qs, ms)

    # 'modules' is now a list of moduleConfig objects. If any of the entries
    #   in mconff had queries that didn't match entries in qconff, that module
    #   was obliterated completely and will be ignored!
    # 'queries' is a list of all the active database sections associated
    #   with the individual modules. It's technically a set, so no dupes.
    # Now we're ready for an actual loop! But let someone else do it.

    return modules, queries

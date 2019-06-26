# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 11 Jun 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from collections import OrderedDict


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

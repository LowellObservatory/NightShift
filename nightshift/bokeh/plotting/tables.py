# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 31 May 2019
#
#  @author: rhamilton

"""Collection of helper routines used when making Bokeh tables.

Further description.
"""

from __future__ import division, print_function, absolute_import

from bokeh.models import DataTable, TableColumn, HTMLTemplateFormatter


def setupTable(cds):
    """
    """
    # Define our color format/template
    #   This uses Underscore’s template method and syntax.
    #   http://underscorejs.org/#template
    template = """
                <b>
                <div style="background:<%=
                    (function ageColorer(){
                        if(ageStatement){
                        return("#ff0000;opacity:0.25;")
                        }
                        else{
                        return("none;")
                        }
                    }()) %>;">
                    <%= value %>
                </div>
                </b>
                """

    formatter = HTMLTemplateFormatter(template=template)

    # Now we construct our table by specifying the columns we actually want.
    #   We ignore the 'ageStatement' row for this because we
    #   just get at it via the formatter/template defined above
    labelCol = TableColumn(field='labels', title='Parameter', sortable=False)
    valueCol = TableColumn(field='values', title='Value', sortable=False,
                           formatter=formatter)
    cols = [labelCol, valueCol]

    nRows = len(cds.data['labels'])

    # Now actually construct the table
    dtab = DataTable(columns=cols, source=cds)

    # THIS IS SO GOD DAMN IRRITATING
    #   It won't accept this in a theme file because it seems like there's a
    #   type check on it and 'None' is not the 'correct' type
    dtab.index_position = None

    # This is also irritating
    #   Specify a css group to be stuffed into the resulting div/template
    #   which is then styled by something else. Can't get it thru the theme :(
    dtab.css_classes = ["nightwatch_bokeh_table"]

    return dtab, nRows

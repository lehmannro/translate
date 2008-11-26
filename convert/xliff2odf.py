#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2004-2006 Zuza Software Foundation
# 
# This file is part of translate.
#
# translate is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# translate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with translate; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

"""convert OpenDocument (ODF) files to Gettext PO localization files"""

import cStringIO
import zipfile
import re

import lxml.etree as etree

from translate.storage import factory
from translate.storage.xml_extract import unit_tree
from translate.storage.xml_extract import extract
from translate.storage.xml_extract import generate
from translate.storage import odf_shared, odf_io
from translate.storage.xml_name import XmlNamer

def first_child(unit_node):
    return unit_node.children.values()[0]

def translate_odf(template, input_file):
    def load_dom_trees(template):
        odf_data = odf_io.open_odf(template)
        return dict((filename, etree.parse(cStringIO.StringIO(data))) for filename, data in odf_data.iteritems())
    
    def load_unit_tree(input_file, dom_trees):
        store = factory.getobject(input_file)
        tree = unit_tree.build_unit_tree(store)

        def extract_unit_tree(filename, root_dom_element_name):
            """Find the subtree in 'tree' which corresponds to the data in XML file 'filename'"""
            def get_tree():
                try:
                    # dom_trees[filename] is an XML document, XmlNamer uses it for its namespace table.
                    # We use XmlNamer to get the full XML name of 'office:?' where ? is the value of
                    # root_dom_element_name. This full XML name is then the index we use in tree.children
                    # to get the tree we want.
                    return tree.children[XmlNamer(dom_trees[filename]).name('office', root_dom_element_name), 0]
                except KeyError:
                    return unit_tree.XPathTree()
            return (filename, get_tree())

        return dict([extract_unit_tree('content.xml', 'document-content'),
                     extract_unit_tree('meta.xml',    'document-meta'),
                     extract_unit_tree('styles.xml',  'document-styles')])

    def translate_dom_trees(unit_trees, dom_trees):
        make_parse_state = lambda: extract.ParseState(odf_shared.no_translate_content_elements, odf_shared.inline_elements)
        for filename, dom_tree in dom_trees.iteritems():
            file_unit_tree = unit_trees[filename]
            generate.apply_translations(dom_tree.getroot(), file_unit_tree, generate.replace_dom_text(make_parse_state))
        return dom_trees

    dom_trees = load_dom_trees(template)
    unit_trees = load_unit_tree(input_file, dom_trees)
    return translate_dom_trees(unit_trees, dom_trees)

def write_odf(template, output_file, dom_trees):

    def write_content_to_odf(output_zip, dom_trees):
        for filename, dom_tree in dom_trees.iteritems():
            output_zip.writestr(filename, etree.tostring(dom_tree, encoding='UTF-8', xml_declaration=True))

    output_zip = odf_io.copy_odf(template, output_file, dom_trees.keys())
    write_content_to_odf(output_zip, dom_trees)

def convertxliff(input_file, output_file, template):
    """reads in stdin using fromfileclass, converts using convertorclass, writes to stdout"""
    dom_trees = translate_odf(template, input_file)
    write_odf(template, output_file, dom_trees)
    return True

def main(argv=None):
    from translate.convert import convert
    formats = {"xlf": ("odt", convertxliff)}
    parser = convert.ConvertOptionParser(formats, usetemplates=True, description=__doc__)
    parser.run(argv)

if __name__ == '__main__':
    main()

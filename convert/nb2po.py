#!/usr/bin/env python
#
# Copyright 2002-2004 Zuza Software Foundation
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

"""Converts nanoblogger HTML part files to Gettext .po files"""

from translate.storage import po
from translate.misc import quote
from translate.storage import html

class nb2po:
  htmlfields = ["BODY"]

  def makepoelement(self, filename, fieldname, fieldvalue):
    """makes a poelement"""
    thepo = po.poelement()
    thepo.sourcecomments.append("#: %s#%s\n" % (filename,fieldname))
    thepo.msgid = []
    lines = fieldvalue.split("\n")
    for linenum in range(len(lines)):
      line = lines[linenum]
      line = quote.escapequotes(line, escapeescapes=1)
      if linenum != len(lines)-1:
        line += "\\n"
      thepo.msgid.append('"' + line + '"')
    if len(thepo.msgid) > 1:
      thepo.msgid = [quote.quotestr("")] + thepo.msgid
    thepo.msgstr = []
    return thepo

  def makepoelements(self, filename, fieldname, fieldvalue):
    """makes a list of poelements from an html block"""
    thepolist = []
    htmlparser = html.POHTMLParser(includeuntaggeddata = True)
    htmlparser.feed(fieldvalue)
    if htmlparser.currentblock.strip():
      htmlparser.blocks.append(htmlparser.currentblock.strip())
    blocknum = 0
    for block in htmlparser.blocks:
      block = block.strip()
      if not block: continue
      if "" in block.split("\n"):
        # split up into separate blocks based on line
        subblock = ""
        for line in block.split("\n"):
          if not line:
            subblock = subblock.strip()
            if subblock:
              thepo = self.makepoelement(filename, "%s:%d" % (fieldname, blocknum), subblock)
              thepolist.append(thepo)
            subblock = ""
          else:
            subblock += line + "\n"
          blocknum += 1
        subblock = subblock.strip()
        if subblock:
          thepo = self.makepoelement(filename, "%s:%d" % (fieldname, blocknum), subblock)
          thepolist.append(thepo)
      else:
        thepo = self.makepoelement(filename, "%s:%d" % (fieldname, blocknum), block)
        thepolist.append(thepo)
        blocknum += 1
    return thepolist

  def convertfile(self, inputfile, filename, includeheader):
    """converts a file to .po format"""
    thepofile = po.pofile()
    if includeheader:
      headerpo = thepofile.makeheader(charset="UTF-8", encoding="8bit")
      thepofile.poelements.append(headerpo)
    lines = inputfile.readlines()
    inlongfield = False
    for line in lines:
      if line.strip() == "-----":
        if inlongfield:
          thepolist = self.makepoelements(filename, longfieldname, longfieldvalue)
          thepofile.poelements.extend(thepolist)
        inlongfield = not inlongfield
        longfieldname, longfieldvalue = None, ""
        continue
      if inlongfield and longfieldname is not None:
        longfieldvalue += line
        continue
      colonpos = line.find(":")
      if colonpos == -1:
        continue
      fieldname = line[:colonpos]
      fieldvalue = line[colonpos+1:].strip()
      if inlongfield:
        longfieldname, longfieldvalue = fieldname, fieldvalue
      else:
        # split up into blocks
        thepo = self.makepoelement(filename, fieldname, fieldvalue)
        thepofile.poelements.append(thepo)
    return thepofile

def convertnb(inputfile, outputfile, templates):
  """reads in stdin using fromfileclass, converts using convertorclass, writes to stdout"""
  convertor = nb2po()
  outputfilepos = outputfile.tell()
  includeheader = outputfilepos == 0
  outputpo = convertor.convertfile(inputfile, getattr(inputfile, "name", "unknown"), includeheader)
  outputpolines = outputpo.tolines()
  outputfile.writelines(outputpolines)
  return 1

def main():
  from translate.convert import convert
  formats = {"htm":("po",convertnb)}
  parser = convert.ConvertOptionParser(formats, usepots=True, description=__doc__)
  parser.run()


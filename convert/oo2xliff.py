#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2003-2006 Zuza Software Foundation
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

"""Converts OpenOffice.org exported .oo files to xliff files"""

import os
from translate.storage import xliff
from translate.storage import oo
from translate.misc import quote
from translate import __version__

# TODO: support using one GSI file as template, another as input (for when English is in one and translation in another)

class oo2xliff:
  def __init__(self, sourcelanguage, targetlanguage, blankmsgstr=False, long_keys=False):
    """construct an oo2xliff converter for the specified languages"""
    self.sourcelanguage = sourcelanguage
    self.targetlanguage = targetlanguage
    self.blankmsgstr = blankmsgstr
    self.long_keys = long_keys

  def makexliffunit(self, part1, part2, translators_comment, key, subkey):
    """makes a xliff element out of a subkey of two parts"""
    #TODO: Do better
    text1 = getattr(part1, subkey).replace("\\\\", "\a").replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r").replace("\a", "\\")
    text2 = getattr(part2, subkey).replace("\\\\", "\a").replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r").replace("\a", "\\")

    unit = xliff.xliffunit(text1)
    unit.target = text2
    unit.addnote(key + "." + subkey + "\n", origin="location")
    if getattr(translators_comment, subkey).strip() != "":
      unit.addnote("%s" % getattr(translators_comment, subkey), origin="developer")
    return unit

  def makekey(self, ookey):
    """converts an oo key tuple into a key identifier for the xliff file"""
    project, sourcefile, resourcetype, groupid, localid, platform = ookey
    sourcefile = sourcefile.replace('\\','/')
    if self.long_keys:
      sourcebase = os.path.join(project, sourcefile)
    else:
      sourceparts = sourcefile.split('/')
      sourcebase = "".join(sourceparts[-1:])
    if (groupid) == 0 or len(localid) == 0:
      ooid = groupid + localid
    else:
      ooid = groupid + "." + localid
    if resourcetype:
      ooid = ooid + "." + resourcetype
    key = "%s#%s" % (sourcebase, ooid)
    return oo.normalizefilename(key)

  def convertelement(self, theoo):
    """convert an oo element into a list of xliff units"""
    if self.sourcelanguage in theoo.languages:
      part1 = theoo.languages[self.sourcelanguage]
    else:
      print "/".join(theoo.lines[0].getkey()), "language not found: %s" % (self.sourcelanguage)
      return []
    if self.blankmsgstr:
      # use a blank part2
      part2 = oo.ooline()
    else:
      if self.targetlanguage in theoo.languages:
        part2 = theoo.languages[self.targetlanguage]
      else:
        # if the language doesn't exist, the translation is missing ... so make it blank
        part2 = oo.ooline()
    if "x-comment" in theoo.languages:
      translators_comment = theoo.languages["x-comment"]
    else:
      translators_comment = oo.ooline()
    key = self.makekey(part1.getkey())
    textunit = self.makexliffunit(part1, part2, translators_comment, key, 'text')
    quickhelpunit = self.makexliffunit(part1, part2, translators_comment, key, 'quickhelptext')
    titleunit = self.makexliffunit(part1, part2, translators_comment, key, 'title')
    unitlist = [textunit, quickhelpunit, titleunit]
    return unitlist

  def convertfile(self, theoofile, duplicatestyle="msgctxt"):
    """converts an entire oo file to xliff format"""
    thefile = xliff.xlifffile()
    # create a header for the file
    bug_url = 'http://qa.openoffice.org/issues/enter_bug.cgi' + ('''?subcomponent=ui&comment=&short_desc=Localization issue in file: %(filename)s&component=l10n&form_name=enter_issue''' % {"filename": theoofile.filename}).replace(" ", "%20").replace(":", "%3A")
    # go through the oo and convert each element
    for theoo in theoofile.units:
      unitlist = self.convertelement(theoo)
      for unit in unitlist:
        thefile.addunit(unit)
    return thefile

def verifyoptions(options):
  """verifies the commandline options"""
  if not options.targetlanguage:
    raise ValueError("You must specify the target language.")

def convertoo(inputfile, outputfile, templates, pot=False, sourcelanguage=None, targetlanguage=None, duplicatestyle="msgid_comment", multifilestyle="single"):
  """reads in stdin using fromfileclass, converts using convertorclass, writes to stdout"""
  fromfile = oo.oofile()
  if hasattr(inputfile, "filename"):
    fromfile.filename = inputfile.filename
  filesrc = inputfile.read()
  fromfile.parse(filesrc)
  if not sourcelanguage:
    testlangtype = targetlanguage or (fromfile and fromfile.languages[0]) or ""
    if testlangtype.isdigit():
      sourcelanguage = "01"
    else:
      sourcelanguage = "en-US"
  if not sourcelanguage in fromfile.languages:
    print "Warning: sourcelanguage %s not found in inputfile (contains %s)" % (sourcelanguage, ", ".join(fromfile.languages))
  if targetlanguage and targetlanguage not in fromfile.languages:
    print "Warning: targetlanguage %s not found in inputfile (contains %s)" % (targetlanguage, ", ".join(fromfile.languages))
  convertor = oo2xliff(sourcelanguage, targetlanguage, blankmsgstr=pot, long_keys=multifilestyle!="single")
  outputxliff = convertor.convertfile(fromfile, duplicatestyle)
  if outputxliff.isempty():
    return 0
  outputxliff = str(outputxliff)
  outputfile.write(outputxliff)
  return 1

def main(argv=None):
  from translate.convert import convert
  formats = {"oo":("xliff",convertoo), "sdf":("xliff",convertoo)}
  # always treat the input as an archive unless it is a directory
  archiveformats = {(None, "input"): oo.oomultifile}
  parser = convert.ArchiveConvertOptionParser(formats, usepots=True, description=__doc__, archiveformats=archiveformats)
  parser.add_option("-l", "--language", dest="targetlanguage", default=None,
    help="set target language to extract from oo file (e.g. af-ZA)", metavar="LANG")
  parser.add_option("", "--source-language", dest="sourcelanguage", default=None, 
                    help="set source language code (default en-US)", metavar="LANG")
  parser.add_option("", "--nonrecursiveinput", dest="allowrecursiveinput", default=True, action="store_false", help="don't treat the input oo as a recursive store")
  parser.add_duplicates_option()
  parser.add_multifile_option()
  parser.passthrough.append("pot")
  parser.passthrough.append("sourcelanguage")
  parser.passthrough.append("targetlanguage")
  parser.verifyoptions = verifyoptions
  parser.run(argv)

if __name__ == '__main__':
    main()
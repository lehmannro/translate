#!/usr/bin/env python
# 
# Copyright 2002, 2003 Zuza Software Foundation
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

"""simple script to convert a comma-separated values (.csv) file to a gettext .po localization file"""

import sys
from translate.misc import quote
from translate.misc import sparse
from translate.storage import po
from translate.storage import csvl10n

def replacestrings(source, *pairs):
  for orig, new in pairs:
    source = source.replace(orig, new)
  return source

def quotecsvstr(source):
  return '"' + replacestrings(source, ('\\"','"'), ('"','\\"'), ("\\\\'", "\\'"), ('\\\\n', '\\n')) + '"'

def simplify(string):
  return filter(type(string).isalnum, string)
  tokens = sparse.SimpleParser().tokenize(string)
  return " ".join(tokens)

class csv2po:
  """a class that takes translations from a .csv file and puts them in a .po file"""
  def __init__(self, templatepo=None, charset=None):
    """construct the converter..."""
    self.pofile = templatepo
    self.charset = charset
    if self.pofile is not None:
      self.unmatched = 0
      self.makeindex()

  def makeindex(self):
    """makes indexes required for searching..."""
    self.sourceindex = {}
    self.msgidindex = {}
    self.simpleindex = {}
    self.duplicatesources = []
    for thepo in self.pofile.poelements:
      sourceparts = []
      for sourcecomment in thepo.sourcecomments:
        sourceparts.append(sourcecomment.replace("#:","",1).strip())
      source = " ".join(sourceparts)
      unquotedid = po.getunquotedstr(thepo.msgid)
      # the definitive way to match is by source
      if source in self.sourceindex:
        # unless more than one thing matches...
        self.duplicatesources.append(source)
      else:
        self.sourceindex[source] = thepo
      # do simpler matching in case things have been mangled...
      simpleid = simplify(unquotedid)
      # but check for duplicates
      if simpleid in self.simpleindex and not (unquotedid in self.msgidindex):
        # keep a list of them...
        self.simpleindex[simpleid].append(thepo)
      else:
        self.simpleindex[simpleid] = [thepo]
      # also match by standard msgid
      self.msgidindex[unquotedid] = thepo
    for source in self.duplicatesources:
      if source in self.sourceindex:
        del self.sourceindex[source]

  def convertelement(self,thecsv):
    """converts csv element to po element"""
    thepo = po.poelement()
    thepo.sourcecomments = ["#: " + thecsv.source + "\n"]
    thepo.msgid = [quotecsvstr(line) for line in thecsv.msgid.split('\n')]
    thepo.msgstr = [quotecsvstr(line) for line in thecsv.msgstr.split('\n')]
    return thepo

  def handlecsvelement(self, thecsv):
    """handles reintegrating a csv element into the .po file"""
    if len(thecsv.source.strip()) > 0 and thecsv.source in self.sourceindex:
      thepo = self.sourceindex[thecsv.source]
    elif thecsv.msgid in self.msgidindex:
      thepo = self.msgidindex[thecsv.msgid]
    elif simplify(thecsv.msgid) in self.simpleindex:
      thepolist = self.simpleindex[simplify(thecsv.msgid)]
      if len(thepolist) > 1:
        print >>sys.stderr, "trying to match by duplicate simpleid: original %s, simplified %s" % (thecsv.msgid, simplify(thecsv.msgid))
        print >>sys.stderr, "\n".join(["possible match: " + po.getunquotedstr(thepo.msgid) for thepo in thepolist])
        self.unmatched += 1
        return
      thepo = thepolist[0]
    else:
      print >>sys.stderr, "could not find csv entry in po: %r, %r, %r" % \
        (thecsv.source, thecsv.msgid, thecsv.msgstr)
      self.unmatched += 1
      return
    csvmsgstr = [quotecsvstr(line) for line in thecsv.msgstr.split('\n')]
    if thepo.hasplural():
      # we need to work out whether we matched the singular or the plural
      singularid = po.getunquotedstr(thepo.msgid)
      pluralid = po.getunquotedstr(thepo.msgid_plural)
      if thecsv.msgid == singularid:
        thepo.msgstr[0] = csvmsgstr
      elif thecsv.msgid == pluralid:
        thepo.msgstr[1] = csvmsgstr
      elif simplify(thecsv.msgid) == simplify(singularid):
        thepo.msgstr[0] = csvmsgstr
      elif simplify(thecsv.msgid) == simplify(pluralid):
        thepo.msgstr[1] = csvmsgstr
      else:
        print >>sys.stderr, "couldn't work out singular or plural: %r, %r, %r" %  \
          (thecsv.msgid, singularid, pluralid)
        self.unmatched += 1
        return
    else:
      thepo.msgstr = csvmsgstr

  def convertfile(self, thecsvfile):
    """converts a csvfile to a pofile, and returns it. uses templatepo if given at construction"""
    if self.pofile is None:
      self.pofile = po.pofile()
      mergemode = False
    else:
      mergemode = True
    if self.pofile.poelements and self.pofile.poelements[0].isheader():
      headerpo = self.pofile.poelements[0]
      headerpo.msgstr = [line.replace("CHARSET", "UTF-8").replace("ENCODING", "8bit") for line in headerpo.msgstr]
    else:
      headerpo = self.pofile.makeheader(charset="UTF-8", encoding="8bit")
    headerpo.othercomments.append("# extracted from %s\n" % thecsvfile.filename)
    mightbeheader = True
    for thecsv in thecsvfile.csvelements:
      if self.charset is not None:
        thecsv.msgid = thecsv.msgid.decode(self.charset)
        thecsv.msgstr = thecsv.msgstr.decode(self.charset)
      if mightbeheader:
        # ignore typical header strings...
        mightbeheader = False
        if [item.strip().lower() for item in thecsv.source, thecsv.msgid, thecsv.msgstr] == \
           ["source", "original", "translation"]:
          continue
        if len(thecsv.source.strip()) == 0 and thecsv.msgid.find("Content-Type:") != -1:
          continue
      if mergemode:
        self.handlecsvelement(thecsv)
      else:
        thepo = self.convertelement(thecsv)
        self.pofile.poelements.append(thepo)
    return self.pofile

  def getmissing(self):
    """get the number of missing translations..."""
    # TODO: work out how to print out the following if in verbose mode
    missing = 0
    for thepo in self.pofile.poelements:
      if thepo.isblankmsgstr():
        missing += 1

def convertcsv(inputfile, outputfile, templatefile, charset=None):
  """reads in inputfile using csvl10n, converts using csv2po, writes to outputfile"""
  inputcsv = csvl10n.csvfile(inputfile)
  if templatefile is None:
    convertor = csv2po(charset=charset)
  else:
    templatepo = po.pofile(templatefile)
    convertor = csv2po(templatepo, charset=charset)
  outputpo = convertor.convertfile(inputcsv)
  if outputpo.isempty():
    return 0
  outputpolines = outputpo.tolines()
  outputfile.writelines(outputpolines)
  return 1

def main():
  from translate.convert import convert
  formats = {("csv", "po"): ("po", convertcsv), ("csv", "pot"): ("po", convertcsv), 
             ("csv", None): ("po", convertcsv)}
  parser = convert.ConvertOptionParser(formats, usetemplates=True, description=__doc__)
  parser.add_option("", "--charset", dest="charset", default=None,
    help="set charset to decode from csv files", metavar="CHARSET")
  parser.passthrough.append("charset")
  parser.run()


#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2002-2006 Zuza Software Foundation
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

"""script to convert a mozilla .dtd UTF-8 localization format to a
gettext .po localization file using the po and dtd modules, and the 
dtd2po convertor class which is in this module
You can convert back to .dtd using po2dtd.py"""

import sys
from translate.storage import po
from translate.storage import dtd
from translate.misc import quote
from translate import __version__

class dtd2po:
  def __init__(self, blankmsgstr=False, duplicatestyle="msgid_comment"):
    self.currentgroup = None
    self.blankmsgstr = blankmsgstr
    self.duplicatestyle = duplicatestyle

  def convertcomments(self,thedtd,thepo):
    entity = quote.rstripeol(thedtd.entity)
    if len(entity) > 0:
      thepo.sourcecomments.append("#: " + thedtd.entity + "\n")
    for commenttype,comment in thedtd.comments:
      # handle groups
      if (commenttype == "locgroupstart"):
        groupcomment = comment.replace('BEGIN','GROUP')
        self.currentgroup = groupcomment
      elif (commenttype == "locgroupend"):
        groupcomment = comment.replace('END','GROUP')
        self.currentgroup = None
      # handle msgidcomments
      if commenttype == "msgidcomment":
        thepo.msgidcomments.append(comment + "\n")
      # handle normal comments
      else:
        thepo.othercomments.append("# " + quote.stripcomment(comment) + "\n")
    # handle group stuff
    if self.currentgroup is not None:
      thepo.othercomments.append("# " + quote.stripcomment(self.currentgroup) + "\n")
    if entity.endswith(".height") or entity.endswith(".width") or entity.endswith(".size"):
      thepo.msgidcomments.append(quote.quotestr("_: Do not translate this.  Only change the numeric values if you need this dialogue box to appear bigger.\\n"))

  def convertstrings(self,thedtd,thepo):
    # extract the string, get rid of quoting
    unquoted = dtd.unquotefromdtd(thedtd.definition).replace("\r", "")
    # escape backslashes... but not if they're for a newline
    # unquoted = unquoted.replace("\\", "\\\\").replace("\\\\n", "\\n")
    # now split the string into lines and quote them
    lines = [po.escapeforpo(line) for line in unquoted.split('\n')]
    while lines and not lines[0].strip():
      del lines[0]
    while lines and not lines[-1].strip():
      del lines[-1]
    # quotes have been escaped already by escapeforpo, so just add the start and end quotes
    simplequotestr = lambda line: '"' + line + '"'
    if len(lines) > 1:
      thepo.msgid = [simplequotestr(lines[0].rstrip() + ' ')] + \
              [simplequotestr(line.strip() + ' ') for line in lines[1:-1]] + \
              [simplequotestr(lines[-1].lstrip())]
    elif lines:
      thepo.msgid = [simplequotestr(lines[0])]
    else:
      thepo.source = ""
    thepo.target = ""

  def convertelement(self,thedtd):
    """converts a dtd element to a po element, returns None if empty or not for translation"""
    if thedtd is None:
      return None
    if getattr(thedtd, "entityparameter", None) == "SYSTEM":
      return None
    thepo = po.pounit(encoding="UTF-8")
    # remove unwanted stuff
    for commentnum in range(len(thedtd.comments)):
      commenttype,locnote = thedtd.comments[commentnum]
      # if this is a localization note
      if commenttype == 'locnote':
        # parse the locnote into the entity and the actual note
        typeend = quote.findend(locnote,'LOCALIZATION NOTE')
        # parse the id
        idstart = locnote.find('(',typeend)
        if idstart == -1: continue
        idend = locnote.find(')',idstart+1)
        entity = locnote[idstart+1:idend].strip()
        # parse the actual note
        actualnotestart = locnote.find(':',idend+1)
        actualnoteend = locnote.find('-->',idend)
        actualnote = locnote[actualnotestart+1:actualnoteend].strip()
        # if it's for this entity, process it
        if thedtd.entity == entity:
          # if it says don't translate (and nothing more),
          if actualnote.startswith("DONT_TRANSLATE"):
            # take out the entity,definition and the DONT_TRANSLATE comment
            thedtd.entity = ""
            thedtd.definition = ""
            del thedtd.comments[commentnum]
            # finished this for loop
            break
          else:
            # convert it into a msgidcomment, to be processed by convertcomments
            # the actualnote is followed by a literal \n
            thedtd.comments[commentnum] = ("msgidcomment",quote.quotestr("_: "+actualnote+"\\n"))
    # do a standard translation
    self.convertcomments(thedtd,thepo)
    self.convertstrings(thedtd,thepo)
    if thepo.isblank() and not thepo.getlocations():
      return None
    else:
      return thepo

  # labelsuffixes and accesskeysuffixes are combined to accelerator notation
  labelsuffixes = (".label", ".title")
  accesskeysuffixes = (".accesskey", ".accessKey", ".akey")

  def convertmixedelement(self,labeldtd,accesskeydtd):
    labelpo = self.convertelement(labeldtd)
    accesskeypo = self.convertelement(accesskeydtd)
    if labelpo is None:
      return accesskeypo
    if accesskeypo is None:
      return labelpo
    thepo = po.pounit(encoding="UTF-8")
    thepo.sourcecomments += labelpo.sourcecomments
    thepo.sourcecomments += accesskeypo.sourcecomments
    thepo.msgidcomments += labelpo.msgidcomments
    thepo.msgidcomments += accesskeypo.msgidcomments
    thepo.othercomments += labelpo.othercomments
    thepo.othercomments += accesskeypo.othercomments
    # redo the strings from original dtd...
    label = dtd.unquotefromdtd(labeldtd.definition).decode('UTF-8')
    accesskey = dtd.unquotefromdtd(accesskeydtd.definition).decode('UTF-8')
    if len(accesskey) == 0:
      return None
    # try and put the & in front of the accesskey in the label...
    # make sure to avoid muddling up &amp;-type strings
    searchpos = 0
    accesskeypos = -1
    inentity = 0
    accesskeyaltcasepos = -1
    while (accesskeypos < 0) and searchpos < len(label):
      searchchar = label[searchpos]
      if searchchar == '&':
        inentity = 1
      elif searchchar == ';':
        inentity = 0
      else:
        if not inentity:
          if searchchar == accesskey.upper():
            # always prefer uppercase
            accesskeypos = searchpos
          if searchchar == accesskey.lower():
            # take lower case otherwise...
            if accesskeyaltcasepos == -1:
              # only want to remember first altcasepos
              accesskeyaltcasepos = searchpos
              # note: we keep on looping through in hope of exact match
      searchpos += 1
    # if we didn't find an exact case match, use an alternate one if available
    if accesskeypos == -1:
      accesskeypos = accesskeyaltcasepos
    # now we want to handle whatever we found...
    if accesskeypos >= 0:
      label = label[:accesskeypos] + '&' + label[accesskeypos:]
      label = label.encode("UTF-8", "replace")
    else:
      # can't currently mix accesskey if it's not in label
      return None
    # now split the string into lines and quote them, like in convertstrings
    msgid = [quote.quotestr(line) for line in label.split('\n')]
    thepo.msgid = msgid
    thepo.msgstr = ['""']
    return thepo

  def findmixedentities(self, thedtdfile):
    """creates self.mixedentities from the dtd file..."""
    self.mixedentities = {} # those entities which have a .label/.title and .accesskey combined
    for entity in thedtdfile.index.keys():
      for labelsuffix in self.labelsuffixes:
        if entity.endswith(labelsuffix):
          entitybase = entity[:entity.rfind(labelsuffix)]
          # see if there is a matching accesskey in this line, making this a
          # mixed entity
          for akeytype in self.accesskeysuffixes:
            if thedtdfile.index.has_key(entitybase + akeytype):
              # add both versions to the list of mixed entities
              self.mixedentities[entity] = {}
              self.mixedentities[entitybase+akeytype] = {}
          # check if this could be a mixed entity (labelsuffix and ".accesskey")

  def convertdtdunit(self, thedtdfile, thedtd, mixbucket="dtd"):
    """converts a dtd element from thedtdfile to a po element, handling mixed entities along the way..."""
    # keep track of whether acceskey and label were combined
    if thedtd.entity in self.mixedentities:
      # use special convertmixed element which produces one pounit with
      # both combined for the label and None for the accesskey
      alreadymixed = self.mixedentities[thedtd.entity].get(mixbucket, None)
      if alreadymixed:
        # we are successfully throwing this away...
        return None
      elif alreadymixed is None:
        # depending on what we come across first, work out the label and the accesskey
        labeldtd, accesskeydtd = None, None
        labelentity, accesskeyentity = None, None
        for labelsuffix in self.labelsuffixes:
          if thedtd.entity.endswith(labelsuffix):
            entitybase = thedtd.entity[:thedtd.entity.rfind(labelsuffix)]
            for akeytype in self.accesskeysuffixes:
              if thedtdfile.index.has_key(entitybase + akeytype):
                labelentity, labeldtd = thedtd.entity, thedtd
                accesskeyentity = labelentity[:labelentity.rfind(labelsuffix)]+akeytype
                accesskeydtd = thedtdfile.index[accesskeyentity]
                break
        else:
          for akeytype in self.accesskeysuffixes:
            if thedtd.entity.endswith(akeytype):
              accesskeyentity, accesskeydtd = thedtd.entity, thedtd
              for labelsuffix in self.labelsuffixes:
                labelentity = accesskeyentity[:accesskeyentity.rfind(akeytype)]+labelsuffix
                if thedtdfile.index.has_key(labelentity):
                  labeldtd = thedtdfile.index[labelentity]
                  break
        thepo = self.convertmixedelement(labeldtd, accesskeydtd)
        if thepo is not None:
          if accesskeyentity is not None:
            self.mixedentities[accesskeyentity][mixbucket] = True
          if labelentity is not None:
            self.mixedentities[labelentity][mixbucket] = True
          return thepo
        else:
          # otherwise the mix failed. add each one separately and remember they weren't mixed
          if accesskeyentity is not None:
            self.mixedentities[accesskeyentity][mixbucket] = False
          if labelentity is not None:
            self.mixedentities[labelentity][mixbucket] = False
    return self.convertelement(thedtd)

  def convertfile(self, thedtdfile):
    thepofile = po.pofile()
    headerpo = thepofile.makeheader(charset="UTF-8", encoding="8bit", x_accelerator_marker="&")
    headerpo.othercomments.append("# extracted from %s\n" % thedtdfile.filename)
    thepofile.units.append(headerpo)
    thedtdfile.makeindex()
    self.findmixedentities(thedtdfile)
    # go through the dtd and convert each element
    for thedtd in thedtdfile.units:
      if thedtd.isnull():
        continue
      thepo = self.convertdtdunit(thedtdfile, thedtd)
      if thepo is not None:
        thepofile.units.append(thepo)
    thepofile.removeduplicates(self.duplicatestyle)
    return thepofile

  def mergefiles(self, origdtdfile, translateddtdfile):
    thepofile = po.pofile()
    headerpo = thepofile.makeheader(charset="UTF-8", encoding="8bit")
    headerpo.othercomments.append("# extracted from %s, %s\n" % (origdtdfile.filename, translateddtdfile.filename))
    thepofile.units.append(headerpo)
    origdtdfile.makeindex()
    self.findmixedentities(origdtdfile)
    translateddtdfile.makeindex()
    self.findmixedentities(translateddtdfile)
    # go through the dtd files and convert each element
    for origdtd in origdtdfile.units:
      if origdtd.isnull():
        continue
      origpo = self.convertdtdunit(origdtdfile, origdtd, mixbucket="orig")
      if origdtd.entity in self.mixedentities:
        mixedentitydict = self.mixedentities[origdtd.entity]
        if "orig" not in mixedentitydict:
          # this means that the entity is mixed in the translation, but not the original - treat as unmixed
          mixbucket = "orig"
          del self.mixedentities[origdtd.entity]
        elif mixedentitydict["orig"]:
          mixbucket = "orig"
        else:
          mixbucket = "translate"
      else:
        mixbucket = "translate"
      if origpo is None:
        # this means its a mixed entity (with accesskey) that's already been dealt with)
        continue
      if origdtd.entity in translateddtdfile.index:
        translateddtd = translateddtdfile.index[origdtd.entity]
        translatedpo = self.convertdtdunit(translateddtdfile, translateddtd, mixbucket=mixbucket)
      else:
        translatedpo = None
      if origpo is not None:
        if translatedpo is not None and not self.blankmsgstr:
          origpo.msgstr = translatedpo.msgid
        thepofile.units.append(origpo)
    thepofile.removeduplicates(self.duplicatestyle)
    return thepofile

def convertdtd(inputfile, outputfile, templatefile, pot=False, duplicatestyle="msgid_comment"):
  """reads in inputfile and templatefile using dtd, converts using dtd2po, writes to outputfile"""
  inputdtd = dtd.dtdfile(inputfile)
  convertor = dtd2po(blankmsgstr=pot, duplicatestyle=duplicatestyle)
  if templatefile is None:
    outputpo = convertor.convertfile(inputdtd)
  else:
    templatedtd = dtd.dtdfile(templatefile)
    outputpo = convertor.mergefiles(templatedtd, inputdtd)
  if outputpo.isempty():
    return 0
  outputposrc = str(outputpo)
  outputfile.write(outputposrc)
  return 1

def main(argv=None):
  # handle command line options
  from translate.convert import convert
  formats = {"dtd": ("po", convertdtd), ("dtd", "dtd"): ("po", convertdtd)}
  parser = convert.ConvertOptionParser(formats, usetemplates=True, usepots=True, description=__doc__)
  parser.add_duplicates_option()
  parser.passthrough.append("pot")
  parser.run(argv)

if __name__ == '__main__':
  main()


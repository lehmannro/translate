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

"""class that handles all header functions for a header in a po file"""

from translate.misc import quote
from translate.misc import dictutils
from translate import __version__
import sre
import time

def parseheaderstring(input):
  """Parses an input string with the definition of a PO header and returns 
  the interpreted values as a dictionary"""
  headervalues = dictutils.ordereddict()
  for line in input.split("\n"):
    if not line or ":" not in line:
      continue
    key, value = line.split(":", 1)
    #We don't want unicode keys
    key = str(key.strip())
    headervalues[key] = value.strip()
  return headervalues

def update(existing, add=False, **kwargs):
  """Update an existing header dictionary with the values in kwargs, adding new values 
  only if add is true. 
  @return updated dictionary"""
  headerargs = dictutils.ordereddict()
  fixedargs = dictutils.cidict()
  for key, value in kwargs.items():
    key = key.replace("_", "-")
    if key.islower():
      key = key.title()
    fixedargs[key] = value
  removed = []
  for key in poheader.header_order:
    if existing.has_key(key):
      if key in fixedargs:
        headerargs[key] = fixedargs.pop(key)
      else:
        headerargs[key] = existing[key]
      removed.append(key)
    elif add and fixedargs.has_key(key):
        headerargs[key] = fixedargs.pop(key)
  for key, value in existing.iteritems():
    if not key in removed:
      headerargs[key] = value
  if add:
    for key in fixedargs:
      headerargs[key] = fixedargs[key]
  return headerargs


class poheader:
  """This class implements functionality for manipulation of po file headers.
  This class is a mix-in class and useless on its own. It must be used from all
  classes which represent a po file"""

  x_generator = "Translate Toolkit %s" % __version__.ver

  header_order = [
    "Project-Id-Version",
    "Report-Msgid-Bugs-To",
    "POT-Creation-Date",
    "PO-Revision-Date",
    "Last-Translator",
    "Language-Team",
    "MIME-Version",
    "Content-Type",
    "Content-Transfer-Encoding",
    "Plural-Forms",
    "X-Generator",
    ]

  def makeheaderdict(self, charset="CHARSET", encoding="ENCODING", project_id_version=None, pot_creation_date=None, po_revision_date=None, last_translator=None, language_team=None, mime_version=None, plural_forms=None, report_msgid_bugs_to=None, **kwargs):
    """create a header for the given filename. arguments are specially handled, kwargs added as key: value
    pot_creation_date can be None (current date) or a value (datetime or string)
    po_revision_date can be None (form), False (=pot_creation_date), True (=now), or a value (datetime or string)
    @return a dictionary with the header items"""
    if project_id_version is None:
      project_id_version = "PACKAGE VERSION"
    if pot_creation_date is None or pot_creation_date == True:
      pot_creation_date = time.strftime("%Y-%m-%d %H:%M%z")
    if isinstance(pot_creation_date, time.struct_time):
      pot_creation_date = pot_creation_date.strftime("%Y-%m-%d %H:%M%z")
    if po_revision_date is None:
      po_revision_date = "YEAR-MO-DA HO:MI+ZONE"
    elif po_revision_date == False:
      po_revision_date = pot_creation_date
    elif po_revision_date == True:
      po_revision_date = time.strftime("%Y-%m-%d %H:%M%z")
    if isinstance(po_revision_date, time.struct_time):
      po_revision_date = po_revision_date.strftime("%Y-%m-%d %H:%M%z")
    if last_translator is None:
      last_translator = "FULL NAME <EMAIL@ADDRESS>"
    if language_team is None:
      language_team = "LANGUAGE <LL@li.org>"
    if mime_version is None:
      mime_version = "1.0"
    if plural_forms is None:
      plural_forms = "nplurals=INTEGER; plural=EXPRESSION;"
    if report_msgid_bugs_to is None:
      report_msgid_bugs_to = ""

    defaultargs = dictutils.ordereddict()
    defaultargs["Project-Id-Version"] = project_id_version
    defaultargs["Report-Msgid-Bugs-To"] = report_msgid_bugs_to
    defaultargs["POT-Creation-Date"] = pot_creation_date
    defaultargs["PO-Revision-Date"] = po_revision_date
    defaultargs["Last-Translator"] = last_translator
    defaultargs["Language-Team"] = language_team
    defaultargs["MIME-Version"] = mime_version
    defaultargs["Content-Type"] = "text/plain; charset=%s" % charset
    defaultargs["Content-Transfer-Encoding"] = encoding
    defaultargs["Plural-Forms"] = plural_forms
    defaultargs["X-Generator"] = self.x_generator

    return update(defaultargs, add=True, **kwargs)

  def header(self):
    """Returns the header element, or None. Only the first element is allowed
    to be a header. Note that this could still return an empty header element,
    if present."""
    if len(self.units) == 0:
      return None
    candidate = self.units[0]
    if candidate.isheader():
      return candidate
    else:
      return None

  def parseheader(self):
    """Parses the PO header and returns 
    the interpreted values as a dictionary"""
    header = self.header()
    if not header:
      return {}
    return parseheaderstring(header.target)

  def updateheader(self, add=False, **kwargs):
    """Updates the fields in the PO style header. 
    This will create a header if add == True"""
    header = self.header()
    if not header:
      # FIXME: does not work for xliff files yet
      if add and callable(getattr(self, "makeheader", None)):
        header = self.makeheader(**kwargs)
        self.units.insert(0, header)
    else:
      headeritems = update(self.parseheader(), add, **kwargs)
      headerString = ""
      for key, value in headeritems.items():
        headerString += "%s: %s\n" % (key, value)
      header.target = headerString
      header.markfuzzy(False)  # TODO: check why we do this?
    return header

  def getheaderplural(self):
    """returns the nplural and plural values from the header"""
    header = self.parseheader()
    pluralformvalue = header.get('Plural-Forms', None)
    if pluralformvalue is None:
      return None, None
    nplural = sre.findall("nplurals=(.+?);", pluralformvalue)
    plural = sre.findall("plural=(.+?);?$", pluralformvalue)
    if not nplural or nplural[0] == "INTEGER":
      nplural = None
    else:
      nplural = nplural[0]
    if not plural or plural[0] == "EXPRESSION":
      plural = None
    else:
      plural = plural[0]
    return nplural, plural

  def updateheaderplural(self, nplurals, plural):
    """update the Plural-Form PO header"""
    if isinstance(nplurals, basestring):
      nplurals = int(nplurals)
    self.updateheader( Plural_Forms = "nplurals=%d; plural=%s;" % (nplurals, plural) )
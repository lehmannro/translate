#!/usr/bin/env python

from jToolkit.widgets import widgets
from translate.pootle import pagelayout
from translate.pootle import projects
import os

class PootleIndex(pagelayout.PootlePage):
  """the main page"""
  def __init__(self, session):
    self.instance = session.instance
    introtext = pagelayout.IntroText("<strong>Pootle</strong> is a simple web portal that should allow you to <strong>translate</strong>!")
    nametext = pagelayout.IntroText('The name stands for <b>PO</b>-based <b>O</b>nline <b>T</b>ranslation / <b>L</b>ocalization <b>E</b>ngine, but you may need to read <a href="http://www.thechestnut.com/flumps.htm">this</a>.')
    languagelinks = self.getlanguagelinks()
    contents = [introtext, nametext, languagelinks]
    pagelayout.PootlePage.__init__(self, "Pootle", contents, session)

  def getlanguagelinks(self):
    """gets the links to the languages"""
    languageitems = [self.getlanguageitem(languagecode, language) for languagecode, language in self.instance.languages.iteritems()]
    return pagelayout.Contents(languageitems)

  def getlanguageitem(self, languagecode, language):
    if not hasattr(language, "fullname"):
      language.fullname = languagecode
    bodytitle = '<h3 class="title">%s</h3>' % language.fullname
    bodydescription = pagelayout.ItemDescription(widgets.Link(languagecode+"/", language.fullname))
    body = pagelayout.ContentsItem([bodytitle, bodydescription])
    subprojects = [projects.getproject(subproject) for (subprojectcode, subproject) in language.subprojects.iteritems()]
    subprojectcount = len(subprojects)
    totalstats = {"translated":0, "total":0}
    for subproject in subprojects:
      projectstats = subproject.calculatestats()
      for name, count in projectstats.iteritems():
        totalstats[name] = totalstats.get(name, 0) + count
    translated = totalstats["translated"]
    total = totalstats["total"]
    percentfinished = (translated*100/max(total, 1))
    stats = pagelayout.ItemStatistics("%d subprojects, %d%% translated" % (subprojectcount, percentfinished))
    return pagelayout.Item([body, stats])

class LanguageIndex(pagelayout.PootlePage):
  """the main page"""
  def __init__(self, language, session):
    self.language = language
    self.instance = session.instance
    subprojectlinks = self.getsubprojectlinks()
    pagelayout.PootlePage.__init__(self, "Pootle: "+self.language.fullname, subprojectlinks, session)

  def getsubprojectlinks(self):
    """gets the links to the projects"""
    subprojectitems = [self.getsubprojectitem(subprojectcode, subproject) for subprojectcode, subproject in self.language.subprojects.iteritems()]
    return pagelayout.Contents(subprojectitems)

  def getsubprojectitem(self, subprojectcode, subproject):
    bodytitle = '<h3 class="title">%s</h3>' % subproject.fullname
    bodydescription = pagelayout.ItemDescription(widgets.Link(subprojectcode+"/", '%s subproject' % subproject.fullname))
    body = pagelayout.ContentsItem([bodytitle, bodydescription])
    translationproject = projects.getproject(subproject)
    numfiles = len(translationproject.pofilenames)
    projectstats = translationproject.calculatestats()
    translated = projectstats.get("translated", 0)
    total = projectstats.get("total", 0)
    percentfinished = (translated*100/max(total, 1))
    stats = pagelayout.ItemStatistics("%d files, %d/%d strings (%d%%) translated" % (numfiles, translated, total, percentfinished))
    return pagelayout.Item([body, stats])

class SubprojectIndex(pagelayout.PootlePage):
  """the main page"""
  def __init__(self, subproject, session, dirfilter=None):
    self.subproject = subproject
    self.instance = session.instance
    self.translationproject = projects.getproject(self.subproject)
    startlink = pagelayout.IntroText(widgets.Link("translate.html", "Start Translating"))
    processlinks = [startlink]
    if dirfilter is None:
      depth = 0
    else:
      depth = dirfilter.count(os.path.sep) + 1
    direntries = []
    fileentries = []
    for childdir in self.translationproject.browsefiles(dirfilter=dirfilter, depth=depth, includedirs=True, includefiles=False):
      direntry = self.getdiritem(childdir)
      direntries.append(direntry)
    for childfile in self.translationproject.browsefiles(dirfilter=dirfilter, depth=depth, includefiles=True, includedirs=False):
      fileentry = self.getfileitem(childfile)
      fileentries.append(fileentry)
    pagelayout.PootlePage.__init__(self, "Pootle: "+self.subproject.fullname, [processlinks, direntries, fileentries], session)

  def getdiritem(self, direntry):
    basename = os.path.basename(direntry)
    bodytitle = '<h3 class="title">%s</h3>' % basename
    browselink = widgets.Link(basename+"/", 'Browse %s' % basename)
    startlink = widgets.Link("%s/translate.html" % basename, "Start Translating %s" % basename)
    bodydescription = pagelayout.ItemDescription([browselink, startlink])
    pofilenames = self.translationproject.browsefiles(direntry)
    numfiles = len(pofilenames)
    projectstats = self.translationproject.calculatestats(pofilenames)
    translated = projectstats.get("translated", 0)
    total = projectstats.get("total", 0)
    percentfinished = (translated*100/max(total, 1))
    body = pagelayout.ContentsItem([bodytitle, bodydescription])
    stats = pagelayout.ItemStatistics("%d files, %d/%d strings (%d%%) translated" % (numfiles, translated, total, percentfinished))
    return pagelayout.Item([body, stats])

  def getfileitem(self, fileentry):
    basename = os.path.basename(fileentry)
    bodytitle = '<h3 class="title">%s</h3>' % basename
    browselink = widgets.Link('%s?translate=1' % basename, 'Translate %s' % basename)
    downloadlink = widgets.Link(basename, 'Download %s' % basename)
    csvname = basename.replace(".po", ".csv")
    csvlink = widgets.Link(csvname, 'Download %s as csv' % csvname)
    bodydescription = pagelayout.ItemDescription([browselink, downloadlink, csvlink])
    pofilenames = [fileentry]
    projectstats = self.translationproject.calculatestats(pofilenames)
    translated = projectstats.get("translated", 0)
    total = projectstats.get("total", 0)
    percentfinished = (translated*100/max(total, 1))
    body = pagelayout.ContentsItem([bodytitle, bodydescription])
    stats = pagelayout.ItemStatistics("files, %d/%d strings (%d%%) translated" % (translated, total, percentfinished))
    return pagelayout.Item([body, stats])


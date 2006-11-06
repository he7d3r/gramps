#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id: Check.py 7321 2006-09-13 02:57:45Z dallingham $

"Database Processing/Check and repair database"

#-------------------------------------------------------------------------
#
# python modules
#
#-------------------------------------------------------------------------
import os
import cStringIO
import sets
from gettext import gettext as _

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import logging
log = logging.getLogger(".RemoveUnused")

#-------------------------------------------------------------------------
#
# gtk modules
#
#-------------------------------------------------------------------------
import gtk
import gtk.glade

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
import RelLib
import Utils
import const
import ManagedWindow

from PluginUtils import Tool, register_tool
from QuestionDialog import OkDialog, MissingMediaDialog

#-------------------------------------------------------------------------
#
# runTool
#
#-------------------------------------------------------------------------
class RemoveUnused(Tool.BatchTool):
    def __init__(self, dbstate, uistate, options_class, name, callback=None):

        Tool.BatchTool.__init__(self, dbstate, options_class, name)
        if self.fail:
            return

        cli = uistate == None

        if self.db.readonly:
            # TODO: split plugin in a check and repair part to support
            # checking of a read only database
            return
        
        trans = self.db.transaction_begin("",batch=True)
        self.db.disable_signals()
        checker = CheckIntegrity(dbstate, uistate, trans)
        checker.cleanup_events()
        checker.cleanup_sources()

        self.db.transaction_commit(trans, _("Remove unused objects"))
        self.db.enable_signals()
        self.db.request_rebuild()

        errs = checker.build_report(cli)
        if errs:
            Report(uistate, checker.text.getvalue(),cli)

#-------------------------------------------------------------------------
#
#
#
#-------------------------------------------------------------------------
class CheckIntegrity:
    
    def __init__(self, dbstate, uistate, trans):
        self.db = dbstate.db
        self.trans = trans
        self.progress = Utils.ProgressMeter(_('Checking database'),'')

    def cleanup_events(self):
        self.progress.set_pass(_('Removing unused events'),
                               self.db.get_number_of_events())

        self.event_cnt = 0
        for handle in self.db.event_map.keys():
            event = self.db.get_event_from_handle(handle)
            if not self.db.find_backlink_handles(handle):
                self.db.remove_event(handle)
                self.event_cnt += 1

    def cleanup_sources(self):
        self.progress.set_pass(_('Removing unused sources'),
                               self.db.get_number_of_events())

        self.source_cnt = 0
        for handle in self.db.event_map.keys():
            event = self.db.get_event_from_handle(handle)
            if not self.db.find_backlink_handles(handle):
                self.db.remove_event(handle)
                self.source_cnt += 1

    def build_report(self,cl=0):
        self.progress.close()

        errors = self.event_cnt + self.source_cnt
        
        if errors == 0:
            if cl:
                print "No unreferenced objects were found."
            else:
                OkDialog(_("No unreferenced objects were found."),
                         _('The database has passed internal checks'))
            return 0

        self.text = cStringIO.StringIO()
        if self.event_cnt > 0:
            if self.event_cnt == 1:
                self.text.write(_("1 non-referenced event removed\n"))
            else:
                self.text.write(_("%d non-referenced event removed\n") % self.event_cnt)

        if self.source_cnt > 0:
            if self.source_cnt == 1:
                self.text.write(_("1 non-referenced source removed\n"))
            else:
                self.text.write(_("%d non-referenced source removed\n") % self.source_cnt)

        return errors

#-------------------------------------------------------------------------
#
# Display the results
#
#-------------------------------------------------------------------------
class Report(ManagedWindow.ManagedWindow):
    
    def __init__(self, uistate, text, cl=0):
        if cl:
            print text
            return

        ManagedWindow.ManagedWindow.__init__(self, uistate, [], self)
        
        base = os.path.dirname(__file__)
        glade_file = base + os.sep + "summary.glade"
        topDialog = gtk.glade.XML(glade_file,"summary","gramps")
        topDialog.get_widget("close").connect('clicked',self.close)

        window = topDialog.get_widget("summary")
        textwindow = topDialog.get_widget("textwindow")
        textwindow.get_buffer().set_text(text)

        self.set_window(window,
                        topDialog.get_widget("title"),
                        _("Integrity Check Results"))

        self.show()

    def build_menu_names(self, obj):
        return (_('Remove unused objects'), None)

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
class CheckOptions(Tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self,name,person_id=None):
        Tool.ToolOptions.__init__(self,name,person_id)

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
register_tool(
    name = 'remove_unused',
    category = Tool.TOOL_DBFIX,
    tool_class = RemoveUnused,
    options_class = CheckOptions,
    modes = Tool.MODE_GUI | Tool.MODE_CLI,
    translated_name = _("Remove unused objects"),
    status = _("Stable"),
    author_name = "Donald N. Allingham",
    author_email = "don@gramps-project.org",
    description=_("Removes unused objects from the database")
    )

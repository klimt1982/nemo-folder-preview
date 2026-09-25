#!/usr/bin/env python3
# -*- coding: utf-8 -*-

   #########################################################################
 ##                                                                       ##
##           ┏━╸┏━┓╻ ╻┏━╸┏━┓   ╺┳╸╻ ╻╻ ╻┏┳┓┏┓ ┏┓╻┏━┓╻╻  ┏━╸┏━┓            ##
##           ┃  ┃ ┃┃┏┛┣╸ ┣┳┛    ┃ ┣━┫┃ ┃┃┃┃┣┻┓┃┗┫┣━┫┃┃  ┣╸ ┣┳┛            ##
##           ┗━╸┗━┛┗┛ ┗━╸╹┗╸    ╹ ╹ ╹┗━┛╹ ╹┗━┛╹ ╹╹ ╹╹┗━╸┗━╸╹┗╸            ##
##            Nemo Folder Preview — Linux Mint Cinnamon and Nemo          ##
##                                                                        ##
############################################################################
##                                                                        ##
## Cover thumbnailer GUI                                                  ##
##                                                                        ##
## Original copyright (C) 2009 - 2026 Fabien Loison                       ##
## Fork modifications (C) 2026 Lucas Gustavo Quiroga                       ##
##                                                                        ##
## This program is free software: you can redistribute it and/or modify   ##
## it under the terms of the GNU General Public License as published by   ##
## the Free Software Foundation, either version 3 of the License, or      ##
## (at your option) any later version.                                    ##
##                                                                        ##
## This program is distributed in the hope that it will be useful,        ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of         ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          ##
## GNU General Public License for more details.                           ##
##                                                                        ##
## You should have received a copy of the GNU General Public License      ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>.  ##
##                                                                        ##
############################################################################
##                                                                        ##
## UPSTREAM PROJECT : https://github.com/flozz/cover-thumbnailer           ##
##                                                                       ##
#########################################################################


"""Configuration GUI for Nemo Folder Preview.

A GUI for easily configuring Nemo Folder Preview.
"""

__version__ = "0.10.3"
__author__ = "Lucas Gustavo Quiroga (fork maintainer); Fabien Loison (original author)"
__copyright__ = "Copyright © 2026 Lucas Gustavo Quiroga\nBased on Cover Thumbnailer © 2009-2026 Fabien Loison"
__appname__ = "nemo-folder-preview-gui"


import gettext
import os
import re
import shutil
import glob
import hashlib
import subprocess

import gi
gi.require_version("Gtk", "3.0")  # noqa
from gi.repository import Gtk as gtk
from gi.repository import Gio


def _configured_language():
    """Read the preferred UI language before gettext is initialised."""
    home = os.path.expanduser("~")
    config_paths = (
        os.path.join(home, ".config", "nemo-folder-preview", "config.conf"),
        os.path.join(home, ".cover-thumbnailer", "cover-thumbnailer.conf"),
    )
    for config in config_paths:
        section = ""
        try:
            lines = open(config, encoding="utf-8")
        except OSError:
            continue
        with lines:
            for raw_line in lines:
                line = raw_line.strip()
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].lower()
                elif section == "appearance" and line.lower().startswith("language") and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"').lower()
    return "system"


_language = _configured_language()
if _language in ("es", "en"):
    os.environ["LANGUAGE"] = _language

gettext.install(__appname__, localedir="/usr/share/locale")


_system_dark_preference = None


def apply_interface_theme(theme):
    """Apply a preference without changing Cinnamon's global setting."""
    global _system_dark_preference
    settings = gtk.Settings.get_default()
    if _system_dark_preference is None:
        _system_dark_preference = settings.get_property("gtk-application-prefer-dark-theme")
    preference = {
        "dark": True,
        "light": False,
        "system": _system_dark_preference,
    }.get(theme, _system_dark_preference)
    settings.set_property("gtk-application-prefer-dark-theme", preference)


#Base path
if "DEVEL" in os.environ:
    BASE_PATH = "./share/" #For devel
else:
    BASE_PATH = "/usr/share/nemo-folder-preview/"


class Conf(dict):

    """ Import configuration.

    Import configuration from GNOME and inherited settings files
    """

    def __init__(self):
        """ The constructor

        Set the default values
        """
        #Initialize the dictionary
        dict.__init__(self)
        #Pictures
        self['pictures_enabled'] = True
        self['pictures_keepdefaulticon'] = False
        self['pictures_usegnomefolder'] = True
        self['pictures_maxthumbs'] = 3
        self['pictures_theme'] = 'auto'
        self['pictures_paths'] = []
        self['pictures_gnomefolderpath'] = _("<None>")
        # Interface
        self['appearance_theme'] = 'system'
        self['appearance_language'] = 'system'
        #Other
        self['other_enabled'] = True
        #Ignored
        self['ignored_dotted'] = False
        self['ignored_paths'] = []
        #Never ignored
        self['neverignored_paths'] = []
        #Global
        self.user_homedir = os.environ.get("HOME")
        self.user_gnomeconf = os.path.join(
                self.user_homedir,
                ".config/user-dirs.dirs"
                )
        self.user_config_dir = os.path.join(
                self.user_homedir, ".config", "nemo-folder-preview"
                )
        self.user_new_conf = os.path.join(self.user_config_dir, "config.conf")
        self.user_legacy_conf = os.path.join(
                self.user_homedir, ".cover-thumbnailer", "cover-thumbnailer.conf"
                )
        self.user_conf = (
                self.user_new_conf if os.path.isfile(self.user_new_conf)
                else self.user_legacy_conf
                )
        #Read configuration
        self.import_gnome_conf()
        self.import_user_conf()

    def import_gnome_conf(self):
        """Import the XDG Pictures directory from user-dirs.dirs."""
        if not os.path.isfile(self.user_gnomeconf):
            print("W: [%s:Conf.import_gnome_conf] Can't find `user-dirs.dirs' file." % __file__)
            return

        with open(self.user_gnomeconf, 'r') as gnome_conf_file:
            for line in gnome_conf_file:
                match = re.match(r'.*?XDG_PICTURES_DIR.*?=.*?"(.*)".*?', line)
                if not match:
                    continue
                self['pictures_gnomefolderpath'] = match.group(1).replace(
                    '$HOME', self.user_homedir
                )

    def import_user_conf(self):
        """ Import user configuration file. """
        if os.path.isfile(self.user_conf):
            current_section = "unknown"
            user_conf_file = open(self.user_conf, 'r')
            for line in user_conf_file:
                #Comments
                if re.match(r"\s*#.*", line):
                    continue
                #Section
                elif re.match(r"\s*\[([a-z]+)\]\s*", line.lower()):
                    match = re.match(r'\s*\[([a-z]+)\]\s*', line.lower())
                    current_section = match.group(1)
                #Boolean key
                elif re.match(r"\s*([a-z]+)\s*=\s*(yes|no|true|false)\s*", line.lower()):
                    match = re.match(r"\s*([a-z]+)\s*=\s*(yes|no|true|false)\s*", line.lower())
                    key = match.group(1)
                    value = match.group(2)
                    if value in ("yes", "true"):
                        value = True
                    else:
                        value = False
                    self[current_section + "_" + key] = value
                #String keys
                elif re.match(r'\s*(theme|language)\s*=\s*"([^"]+)"\s*', line, re.I):
                    match = re.match(r'\s*(theme|language)\s*=\s*"([^"]+)"\s*', line, re.I)
                    self[current_section + "_" + match.group(1).lower()] = match.group(2).lower()
                #String key : path
                elif re.match(r"\s*(path|PATH|Path)\s*=\s*\"(.+)\"\s*", line):
                    match = re.match(r"\s*(path|PATH|Path)\s*=\s*\"(.+)\"\s*", line)
                    key = "paths"
                    value = match.group(2)
                    target_key = current_section + "_" + key
                    if target_key in self:
                        self[target_key].append(value)
                #Integer key
                elif re.match(r"\s*([a-z]+)\s*=\s*([0-9]+)\s*", line.lower()):
                    match = re.match(r"\s*([a-z]+)\s*=\s*([0-9]+)\s*", line.lower())
                    key = match.group(1)
                    value = match.group(2)
                    self[current_section + "_" + key] = int(value)

            user_conf_file.close()

            #Replace "~/" by the user home dir
            for path_list in (self['pictures_paths'], self['ignored_paths']):
                for i in range(0, len(path_list)):
                    if path_list[i][0] == "~":
                        path_list[i] = os.path.join(self.user_homedir, path_list[i][2:])

            #Import "useGnomeConf" key (for compatibility)
            if "miscellaneous_usegnomeconf" in self:
                self["pictures_usegnomefolder"] = self["miscellaneous_usegnomeconf"]

    def save_user_conf(self):
        """ Save configuration file. """
        #Check if output folder exists, else create it
        conf_dir = self.user_config_dir
        if not os.path.isdir(conf_dir):
            try:
                os.makedirs(conf_dir)
            except OSError: #Permission denied
                print("E: [%s:Conf.save_user_conf] Can't write configuration directory (permission denied)" % __file__)
                return
        try:
            user_conf_file = open(self.user_new_conf, 'w')
            #Warning
            user_conf_file.write('#' + _('Configuration written by Nemo Folder Preview') + "\n")
            user_conf_file.write("#" + _('Please edit with caution') + "\n")
            #Pictures
            user_conf_file.write("\n[PICTURES]\n")
            user_conf_file.write(self._write_bool("pictures_enabled"))
            user_conf_file.write(self._write_bool("pictures_keepdefaulticon"))
            user_conf_file.write(self._write_bool("pictures_usegnomefolder"))
            user_conf_file.write(self._write_int("pictures_maxthumbs"))
            user_conf_file.write('theme = "%s"\n' % self["pictures_theme"])
            user_conf_file.write(self._write_list("pictures_paths"))
            #Appearance
            user_conf_file.write("\n[APPEARANCE]\n")
            user_conf_file.write('theme = "%s"\n' % self["appearance_theme"])
            user_conf_file.write('language = "%s"\n' % self["appearance_language"])
            #Ignored
            user_conf_file.write("\n[IGNORED]\n")
            user_conf_file.write(self._write_bool("ignored_dotted"))
            user_conf_file.write(self._write_list("ignored_paths"))
            #Never ignored
            user_conf_file.write("\n[NEVERIGNORED]\n")
            user_conf_file.write(self._write_list("neverignored_paths"))
            #End
            user_conf_file.write("\n\n") #I like blank lines at the end :)
        except OSError: #Permission denied
            print("E: [%s:Conf.save_user_conf] Can't write configuration (permission denied)" % __file__)
            return
        except IOError: #Input/Output error
            print("E: [%s:Conf.save_user_conf] Can't write configuration (IO error)" % __file__)
            return
        else:
            user_conf_file.close()

    def _write_bool(self, key):
        """ Return the string to write in config file for boolean key

        Argument:
          * key -- the name of the CONF key
        """
        wkey = key.split("_")[1]
        if self[key]:
            value = "Yes"
        else:
            value = "No"
        return "\t%s = %s\n" % (wkey, value)

    def _write_list(self, key):
        """ Return the string to write in config file for list key (path)

        Argument:
          * key -- the name of the CONF key
        """
        result = ""
        for value in self[key]:
            result += "\tpath = \"%s\"\n" % value
        return result

    def _write_int(self, key):
        """ Return the string to write in config file for integer key

        Argument:
          * key -- the name of the CONF key
        """
        wkey = key.split("_")[1]
        value = self[key]
        return "\t%s = %i\n" % (wkey, value)


class MainWin(object):
    """ The configuration GUI """
    def __init__(self):
        win = gtk.Builder()
        win.set_translation_domain(__appname__)
        #FIXME: GtkWarning: Ignoring the separator setting (wtf ?!)
        win.add_from_file(os.path.join(BASE_PATH, "cover-thumbnailer-gui.glade"))

        # Nemo Folder Preview only exposes photo folder previews.
        self.notebook = win.get_object("notebook1")
        appearance_page = win.get_object("vbox11")
        self.notebook.get_tab_label(appearance_page).set_text(_("Appearance"))
        win.get_object("label15").set_text(_("Appearance and maintenance"))

        self.winAbout = win.get_object("winAbout")
        self.winAbout.connect("response", self.on_winAbout_response)
        self.winAbout.set_program_name("Nemo Folder Preview")
        self.winAbout.set_version(__version__)
        self.winAbout.set_copyright(__copyright__)
        self.winAbout.set_website(None)
        self.winAbout.set_comments(
            _("Photo folder previews for Linux Mint Cinnamon and Nemo.")
        )
        self.winAbout.set_authors([
            "Lucas Gustavo Quiroga - fork development and maintenance",
            "Fabien Loison - original Cover Thumbnailer author",
        ])

        ### PICTURES ###
        #Pictures path list
        self.trvPicturesPathList = win.get_object("trvPicturesPathList")
        self.lsstPicturesPathList = gtk.ListStore(str)
        self.trvPicturesPathList.set_model(self.lsstPicturesPathList)
        self.columnPicturesPathList = gtk.TreeViewColumn("Path", gtk.CellRendererText(), text=0)
        self.trvPicturesPathList.append_column(self.columnPicturesPathList)
        #PicturesRemove button
        self.btnPicturesRemove = win.get_object("btnPicturesRemove")
        #GNOME picture folder checkBox
        self.cb_useGnomePictures = win.get_object("cb_useGnomePictures")
        #Enable checkBox
        self.cbPicturesEnable = win.get_object("cbPicturesEnable")
        #KeepIcon checkBox
        self.cbPicturesKeepFIcon = win.get_object("cbPicturesKeepFIcon")
        #spinbtn_maxThumbs Spin Button
        self.spinbtn_maxThumbs = win.get_object("spinbtn_maxThumbs")

        # Folder theme selector
        self.cmbPicturesTheme = gtk.ComboBoxText()
        self.cmbPicturesTheme.append("auto", _("Automatic (current Cinnamon theme)"))
        for theme in sorted(
                item for item in os.listdir("/usr/share/icons")
                if item.startswith("Mint-Y")
        ):
            self.cmbPicturesTheme.append(theme, theme)

        theme_row = gtk.Box(spacing=5)
        theme_label = gtk.Label(label=_("Folder theme:"))
        theme_label.set_xalign(0)
        theme_row.pack_start(theme_label, False, False, 0)
        theme_row.pack_start(self.cmbPicturesTheme, True, True, 0)
        win.get_object("vbox9").pack_start(theme_row, False, False, 5)
        self.cmbPicturesTheme.connect(
            "changed", self.on_cmbPicturesTheme_changed
        )
        theme_row.show_all()

        ### IGNORED ###
        #Ignored path list
        self.trvIgnoredPathList = win.get_object("trvIgnoredPathList")
        self.lsstIgnoredPathList = gtk.ListStore(str)
        self.trvIgnoredPathList.set_model(self.lsstIgnoredPathList)
        self.columnIgnoredPathList = gtk.TreeViewColumn("Path", gtk.CellRendererText(), text=0)
        self.trvIgnoredPathList.append_column(self.columnIgnoredPathList)
        #IgnoredRemove button
        self.btnIgnoredRemove = win.get_object("btnIgnoredRemove")
        #IgnoreHidden checkBox
        self.cbIgnoreHidden = win.get_object("cbIgnoreHidden")

        ### NEVER IGNORED ###
        #Never ignored path list
        self.trvNeverIgnoredPathList = win.get_object("trvNeverIgnoredPathList")
        self.lsstNeverIgnoredPathList = gtk.ListStore(str)
        self.trvNeverIgnoredPathList.set_model(self.lsstNeverIgnoredPathList)
        self.columnNeverIgnoredPathList = gtk.TreeViewColumn("Path", gtk.CellRendererText(), text=0)
        self.trvNeverIgnoredPathList.append_column(self.columnNeverIgnoredPathList)
        #NeverIgnoredRemove button
        self.btnNeverIgnoredRemove = win.get_object("btnNeverIgnoredRemove")

        ### MISCELLANEOUS ###
        #Enable Nemo Folder Preview checkBox
        self.cbEnableCT = win.get_object("cbEnableCT")
        #Thumbnail size spinbtn
        self.spinbtn_thumbSize = win.get_object("spinbtn_thumbSize")

        # Appearance controls are added here instead of altering the legacy Glade layout.
        appearance_box = win.get_object("vbox12")
        appearance_box.pack_start(gtk.Separator(), False, False, 4)
        heading = gtk.Label(label=_("Interface preferences"))
        heading.set_xalign(0)
        appearance_box.pack_start(heading, False, False, 0)

        self.cmbInterfaceTheme = gtk.ComboBoxText()
        self.cmbInterfaceTheme.append("system", _("Use system setting"))
        self.cmbInterfaceTheme.append("light", _("Light"))
        self.cmbInterfaceTheme.append("dark", _("Dark"))
        theme_row = gtk.Box(spacing=8)
        theme_label = gtk.Label(label=_("Interface theme:"))
        theme_label.set_xalign(0)
        theme_row.pack_start(theme_label, False, False, 0)
        theme_row.pack_start(self.cmbInterfaceTheme, True, True, 0)
        appearance_box.pack_start(theme_row, False, False, 0)

        self.cmbInterfaceLanguage = gtk.ComboBoxText()
        self.cmbInterfaceLanguage.append("system", _("System language"))
        self.cmbInterfaceLanguage.append("es", _("Spanish"))
        self.cmbInterfaceLanguage.append("en", _("English"))
        language_row = gtk.Box(spacing=8)
        language_label = gtk.Label(label=_("Language:"))
        language_label.set_xalign(0)
        language_row.pack_start(language_label, False, False, 0)
        language_row.pack_start(self.cmbInterfaceLanguage, True, True, 0)
        appearance_box.pack_start(language_row, False, False, 0)
        restart_note = gtk.Label(label=_("Language changes take effect when you reopen Nemo Folder Preview."))
        restart_note.set_xalign(0)
        restart_note.set_line_wrap(True)
        appearance_box.pack_start(restart_note, False, False, 0)

        self.cmbInterfaceTheme.connect("changed", self.on_cmbInterfaceTheme_changed)
        self.cmbInterfaceLanguage.connect("changed", self.on_cmbInterfaceLanguage_changed)
        appearance_box.show_all()

        ### FileChooser Dialog ###
        self.fileChooser = win.get_object("filechooserdialog")
        self.fileChooserFor = None

        ### ERROR DIALOG file already in list ###
        self.msgdlgErrorPAIL = win.get_object("msgdlgErrorPAIL")

        ### INFO DIALOG generating thumbnails ###
        self.msgdlgGeneratingThumbnails = win.get_object("msgdlgGeneratingThumbnails")

        loadInterface(self) #Put config on the gui
        win.connect_signals(self)

    def on_cmbInterfaceTheme_changed(self, widget):
        theme = self.cmbInterfaceTheme.get_active_id()
        if theme:
            CONF['appearance_theme'] = theme
            apply_interface_theme(theme)

    def on_cmbInterfaceLanguage_changed(self, widget):
        language = self.cmbInterfaceLanguage.get_active_id()
        if language:
            CONF['appearance_language'] = language

    ### WINMAIN ###
    def on_winMain_destroy(self, widget):
        gtk.main_quit()

    def on_btnAbout_clicked(self, widget):
        self.winAbout.show()

    def on_btnCancel_clicked(self, widget):
        gtk.main_quit()

    def on_btnOk_clicked(self, widget):
        CONF.save_user_conf()
        gtk.main_quit()

    #~~~ PICTURES ~~~
    def on_cbPicturesEnable_toggled(self, widget):
        CONF['pictures_enabled'] = self.cbPicturesEnable.get_active()

    def on_cbPicturesKeepFIcon_toggled(self, widget):
        CONF['pictures_keepdefaulticon'] = self.cbPicturesKeepFIcon.get_active()

    def on_btnPicturesAdd_clicked(self, widget):
        self.fileChooserFor = 'pictures'
        self.fileChooser.show()

    def on_trvPicturesPathList_cursor_changed(self, widget):
        model, iter_ = widget.get_selection().get_selected()
        if iter_ is not None:
            self.btnPicturesRemove.set_sensitive(True)

    def on_btnPicturesRemove_clicked(self, widget):
        removePathFromList(
                self.trvPicturesPathList,
                self.lsstPicturesPathList,
                CONF['pictures_paths']
                )
        self.btnPicturesRemove.set_sensitive(False)

    def on_spinbtn_maxThumbs_value_changed(self, widget):
        CONF['pictures_maxthumbs'] = int(self.spinbtn_maxThumbs.get_value())

    def on_cmbPicturesTheme_changed(self, widget):
        theme = self.cmbPicturesTheme.get_active_id()
        if theme:
            CONF['pictures_theme'] = theme

    def on_cb_useGnomePictures_toggled(self, widget):
        CONF['pictures_usegnomefolder'] = self.cb_useGnomePictures.get_active()

    #~~~ IGNORED ~~~
    def on_btnIgnoredAdd_clicked(self, widget):
        self.fileChooserFor = 'ignored'
        self.fileChooser.show()

    def on_trvIgnoredPathList_cursor_changed(self, widget):
        model, iter_ = widget.get_selection().get_selected()
        if iter_ is not None:
            self.btnIgnoredRemove.set_sensitive(True)

    def on_btnIgnoredRemove_clicked(self, widget):
        removePathFromList(self.trvIgnoredPathList, self.lsstIgnoredPathList, CONF['ignored_paths'])
        self.btnIgnoredRemove.set_sensitive(False)

    def on_cbIgnoreHidden_toggled(self, widget):
        CONF['ignored_dotted'] = self.cbIgnoreHidden.get_active()

    #~~~ NEVER IGNORED ~~~
    def on_btnNeverIgnoredAdd_clicked(self, widget):
        self.fileChooserFor = 'neverignored'
        self.fileChooser.show()

    def on_trvNeverIgnoredPathList_cursor_changed(self, widget):
        model, iter_ = widget.get_selection().get_selected()
        if iter_ is not None:
            self.btnNeverIgnoredRemove.set_sensitive(True)

    def on_btnNeverIgnoredRemove_clicked(self, widget):
        removePathFromList(self.trvNeverIgnoredPathList, self.lsstNeverIgnoredPathList, CONF['neverignored_paths'])
        self.btnNeverIgnoredRemove.set_sensitive(False)

    #~~~ MISCELLANEOUS ~~~
    def on_btnClearThumbnailCache_clicked(self, widget):
        thumbpath = os.path.join(CONF.user_homedir, '.cache/thumbnails')
        if os.path.isdir(thumbpath):
            shutil.rmtree(thumbpath)

    def on_btnGenerateThumbnails_clicked(self, widget):
        self.fileChooserFor = 'generatethumbnails'
        self.fileChooser.show()

    ### FILECHOOSER DIALOG ###
    def on_btnFileChooserCancel_clicked(self, widget):
        self.fileChooser.hide()

    def on_btnFileChooserOpen_clicked(self, widget):
        self.fileChooser.hide()
        path = self.fileChooser.get_filename()
        if self.fileChooserFor == 'pictures':
            addPathToList(self.lsstPicturesPathList, path, CONF['pictures_paths'])
        elif self.fileChooserFor == 'ignored':
            addPathToList(self.lsstIgnoredPathList, path, CONF['ignored_paths'])
        elif self.fileChooserFor == 'neverignored':
            addPathToList(self.lsstNeverIgnoredPathList, path, CONF['neverignored_paths'])
        elif self.fileChooserFor == 'generatethumbnails':
            self.msgdlgGeneratingThumbnails.show()
            gtk.main_iteration_do(True)
            CONF.save_user_conf()  # Save user conf before generating thumbs
            gtk.main_iteration_do(True)
            generateThumbnails(path)
            self.msgdlgGeneratingThumbnails.hide()
        self.fileChooserFor = None

    def on_filechooserdialog_delete_event(self, widget, response):
        self.fileChooser.hide()
        return True #Don't delete

    ### ABOUT DIALOG ###
    def on_winAbout_delete_event(self, widget, event):
        self.winAbout.hide()
        return True #Don't delete

    def on_winAbout_response(self, widget, response):
        if response < 0:
            self.winAbout.hide()

    ### ERROR DIALOG file already in list ###
    def on_msgdlgErrorPAIL_delete_event(self, widget, event):
        self.msgdlgErrorPAIL.hide()
        return True #Don't delete

    def on_btnErrorPAILClose_clicked(self, widget):
        self.msgdlgErrorPAIL.hide()


def list_folders(base_path):
    return glob.glob(os.path.join(base_path, "**/"), recursive=True)


def generate_thumbnail_path(path):
    gvfs = Gio.Vfs.get_default()
    uri = gvfs.get_file_for_path(path).get_uri()
    uri = uri.encode("utf-8")
    uri_hash = hashlib.md5(uri).hexdigest()
    return os.path.join(
            CONF.user_homedir,
            '.cache/thumbnails/normal',
            '%s.png' % uri_hash)


def generateThumbnails(path):
    CT_CMD = 'nemo-folder-preview'
    if "DEVEL" in os.environ:
        CT_CMD = './cover-thumbnailer.py'
    for input_folder in list_folders(path):
        gtk.main_iteration_do(False)
        print('Generating thumbnail for %s' % input_folder)
        output_file = generate_thumbnail_path(input_folder)
        print('  -> dest: %s' % output_file)
        subprocess.run([CT_CMD, input_folder, output_file])


def addPathToList(gtklist, path, conflist):
    """ Adds the path in the list

    Arguments:
      * path -- the path to add
      * gtklist -- the gtkListStore where we will add the path
      * confilst -- the "Conf" path list
    """
    if not path in conflist:
        gtklist.append([path])
        conflist.append(path)
    else:
        gui.msgdlgErrorPAIL.show()


def removePathFromList(gtktree, gtklist, conflist):
    """ Remove the path from the list

    Arguments:
      * gtktree -- the gtkTreeView
      * gtklist -- the gtkListStore where we will add the path
      * confilst -- the "Conf" path list
    """
    model, iter_ = gtktree.get_selection().get_selected()
    conflist.remove(gtklist.get_value(iter_, 0))
    gtklist.remove(iter_)


def loadInterface(gui):
    """ Put options on the GUI

    Argument:
      * gui -- the gui
    """
    #Pictures
    gui.cbPicturesEnable.set_active(CONF['pictures_enabled'])
    gui.cbPicturesKeepFIcon.set_active(CONF['pictures_keepdefaulticon'])
    for path in CONF['pictures_paths']:
        gui.lsstPicturesPathList.append([path])
    gui.cb_useGnomePictures.set_label(_("Enable for GNOME's picture folder (%s)") %(CONF['pictures_gnomefolderpath']))
    gui.cb_useGnomePictures.set_active(CONF['pictures_usegnomefolder'])
    if CONF['pictures_maxthumbs'] > 4:
        gui.spinbtn_maxThumbs.set_value(4)
    elif CONF['pictures_maxthumbs'] < 1:
        gui.spinbtn_maxThumbs.set_value(1)
    else:
        gui.spinbtn_maxThumbs.set_value(CONF['pictures_maxthumbs'])
    if not gui.cmbPicturesTheme.set_active_id(CONF['pictures_theme']):
        gui.cmbPicturesTheme.set_active_id("auto")
    if not gui.cmbInterfaceTheme.set_active_id(CONF['appearance_theme']):
        gui.cmbInterfaceTheme.set_active_id("system")
    if not gui.cmbInterfaceLanguage.set_active_id(CONF['appearance_language']):
        gui.cmbInterfaceLanguage.set_active_id("system")
    #Ignored
    gui.cbIgnoreHidden.set_active(CONF['ignored_dotted'])
    for path in CONF['ignored_paths']:
        gui.lsstIgnoredPathList.append([path])
    #Ignored
    for path in CONF['neverignored_paths']:
        gui.lsstNeverIgnoredPathList.append([path])
    #If GNOME folders == user home dir or not defined,
    #deactivate the option, it's probably a misconfiguration !
    if os.path.isdir(CONF['pictures_gnomefolderpath']) \
        and os.path.samefile(CONF['pictures_gnomefolderpath'], CONF.user_homedir) \
        or CONF['pictures_gnomefolderpath'] == _("<None>"):
        gui.cb_useGnomePictures.set_active(False)
        gui.cb_useGnomePictures.set_sensitive(False)


if __name__ == "__main__":
    CONF = Conf()
    apply_interface_theme(CONF["appearance_theme"])
    gui = MainWin()
    gtk.main()

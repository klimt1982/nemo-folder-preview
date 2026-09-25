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
## Cover thumbnailer                                                      ##
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


"""Generates thumbnails for nautilus' folders.

Nemo Folder Preview generates thumbnails that are displayed instead of the
photo folder previews in Nemo using the active Mint-Y icon theme.

Usage:
    nemo-folder-preview <directory's path> <output thumbnail's path>
"""

__version__ = "0.1.0"
__author__ = "Fabien LOISON <http://www.flozz.fr/>"
__copyright__ = "Copyright © 2009 - 2026 Fabien LOISON"


import re
import sys
import os.path
from gi.repository import Gio

try:
    from PIL import Image
except:
    import Image


#==================================================================== CONF ====
# Base path for application assets
if "DEVEL" in os.environ:
    BASE_PATH = "./share/" #For devel
else:
    BASE_PATH = "/usr/share/nemo-folder-preview/"

#Supported picture ext (ALWAY LAST 4 CHARS !!)
# Supported picture extensions
PICTURES_EXT = {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico",
        ".tga", ".tif", ".tiff", ".psd", ".webp",
        }

#==============================================================================


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
        self['pictures_fg'] = os.path.join(BASE_PATH, "pictures_fg.png")
        self['pictures_bg'] = os.path.join(BASE_PATH, "pictures_bg.png")
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
        self.import_user_conf()
        self.import_gnome_conf()

    def import_gnome_conf(self):
        """Import the XDG Pictures directory from user-dirs.dirs."""
        if not os.path.isfile(self.user_gnomeconf):
            print("W: [%s:Conf.import_gnome_conf] Can't find `user-dirs.dirs' file." % __file__)
            return

        with open(self.user_gnomeconf, 'r') as gnome_conf_file:
            for line in gnome_conf_file:
                match = re.match(r'.*?XDG_PICTURES_DIR.*?=.*?"(.*)".*?', line)
                if not match or not self['pictures_usegnomefolder']:
                    continue
                path = match.group(1).replace('$HOME', self.user_homedir)
                if os.path.isdir(path) and not os.path.samefile(path, self.user_homedir):
                    self['pictures_paths'].append(path)

    def import_user_conf(self):
        """ Import user configuration file. """
        if os.path.isfile(self.user_conf):
            current_section = "unknown"
            with open(self.user_conf, "r") as user_conf_file:
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
                    #String key : theme
                    elif re.match(r'\s*theme\s*=\s*"([^"]+)"\s*', line, re.I):
                        self[current_section + "_theme"] = re.match(
                            r'\s*theme\s*=\s*"([^"]+)"\s*', line, re.I
                        ).group(1)
                    #String key : theme
                    elif re.match(r'\s*theme\s*=\s*"([^"]+)"\s*', line, re.I):
                        self[current_section + "_theme"] = re.match(
                            r'\s*theme\s*=\s*"([^"]+)"\s*', line, re.I
                        ).group(1)
                    #String key : path
                    elif re.match(r"\s*(path|PATH|Path)\s*=\s*\"(.+)\"\s*", line):
                        match = re.match(r"\s*(path|PATH|Path)\s*=\s*\"(.+)\"\s*", line)
                        key = "paths"
                        value = match.group(2)
                        self[current_section + "_" + key].append(value)
                    #Integer key
                    elif re.match(r"\s*([a-z]+)\s*=\s*([0-9]+)\s*", line.lower()):
                        match = re.match(r"\s*([a-z]+)\s*=\s*([0-9]+)\s*", line.lower())
                        key = match.group(1)
                        value = match.group(2)
                        self[current_section + "_" + key] = int(value)

            #Replace "~/" by the user home dir
            for path_list in (self['pictures_paths'], self['ignored_paths']):
                for i in range(0, len(path_list)):
                    if path_list[i][0] == "~":
                        path_list[i] = os.path.join(self.user_homedir, path_list[i][2:])

            #Import legacy global preference for compatibility.
            if "miscellaneous_usegnomeconf" in self:
                self["pictures_usegnomefolder"] = self["miscellaneous_usegnomeconf"]



def _folder_icon_path(theme):
    """Return the best available PNG folder icon for a Mint-Y theme."""
    for size_dir in ("128@2x", "128"):
        candidate = os.path.join(
            "/usr/share/icons", theme, "places", size_dir, "folder.png"
        )
        if os.path.isfile(candidate):
            return candidate
    return None


def prepare_picture_theme(conf, requested_size):
    """Generate a scalable Mint-Y folder frame for picture previews."""
    from PIL import ImageDraw

    try:
        size = int(requested_size)
    except (TypeError, ValueError):
        size = 128
    size = min(max(size, 128), 512)

    theme = conf.get("pictures_theme", "auto")
    if theme == "auto":
        theme = os.popen(
            "gsettings get org.cinnamon.desktop.interface icon-theme 2>/dev/null"
        ).read().strip().strip("'")

    if not theme.startswith("Mint-Y") or "/" in theme:
        theme = "Mint-Y"

    folder_path = _folder_icon_path(theme)
    if folder_path is None:
        theme = "Mint-Y"
        folder_path = _folder_icon_path(theme)
    if folder_path is None:
        raise RuntimeError("Unable to find a Mint-Y folder icon")

    cache_dir = os.path.join(
        os.environ.get("HOME", ""),
        ".cache",
        "nemo-folder-preview",
        "themes",
        theme,
        str(size),
    )
    os.makedirs(cache_dir, exist_ok=True)

    bg_path = os.path.join(cache_dir, "pictures_bg.png")
    fg_path = os.path.join(cache_dir, "pictures_fg.png")

    if not (os.path.isfile(bg_path) and os.path.isfile(fg_path)):
        supersample = 4
        scale = (size / 128) * supersample
        folder = Image.open(folder_path).convert("RGBA")
        sample_x = round(folder.width * 64 / 128)
        sample_y = round(folder.height * 80 / 128)
        base_color = folder.getpixel((sample_x, sample_y))

        def scaled_box(coords):
            return tuple(round(value * scale) for value in coords)

        inner = (14, 42, 114, 110)
        canvas_size = size * supersample

        bg = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(bg)
        draw.rounded_rectangle(
            scaled_box(inner),
            radius=max(1, round(5 * scale)),
            fill=base_color,
        )
        bg.resize((size, size), Image.Resampling.LANCZOS).save(bg_path)

        fg = folder.resize(
            (canvas_size, canvas_size), Image.Resampling.LANCZOS
        )
        alpha = fg.getchannel("A")
        draw = ImageDraw.Draw(alpha)
        draw.rounded_rectangle(
            scaled_box(inner),
            radius=max(1, round(5 * scale)),
            fill=0,
        )
        fg.putalpha(alpha)
        fg.resize((size, size), Image.Resampling.LANCZOS).save(fg_path)

    conf["pictures_bg"] = bg_path
    conf["pictures_fg"] = fg_path


class Thumb(object):
    """ Makes thumbnails.

    Generate thumbnails for all kind of folders
    """
    def __init__(self, img_paths):
        """The constructor.

        Argument:
          * img_paths -- a list of picture path
        """
        self.img = []
        for path in img_paths:
            try:
                img = Image.open(path).convert("RGBA")
            except IOError:
                print("E: [%s:Thumb.__init__] Can't open '%s'." % (__file__, path))
            else:
                self.img.append(img)
        self.thumb = None

    def thumbnailize(self, image, twidth=128, theight=128, crop=True):
        """ Make thumbnail.

        Crop the picture if necessaries and return a thumbnail of it.

        Keyword argument:
          * twidth -- the width of the thumbnail (in pixels).
          * theight -- the width of the thumbnail (in pixels).
            NOTE: useless if crop = True
          * crop -- the resize method (True for having a squared thumbnail)

        NOTE: the size shouldn't be greater than 128 px for a standard
              freedesktop thumbnail.
        """
        width = image.size[0]
        height = image.size[1]
        if crop and width >= twidth and height >= theight:
            if width > height:
                left = int((width - height) / 2)
                upper = 0
                right = height + left
                lower = height
            else:
                left = 0
                upper = int((height - width) / 2)
                right = width
                lower = width + upper
            image = image.crop((left, upper, right, lower))
        image.thumbnail((twidth, theight), Image.LANCZOS)
        return image

    def pictures_thumbnail(self, bg_picture, fg_picture, max_pictures=3):
        """Create a scalable Mint-Y-style folder preview for picture folders."""
        bg = Image.open(bg_picture).convert("RGBA")
        scale_x = bg.width / 128
        scale_y = bg.height / 128

        left = round(14 * scale_x)
        top = round(42 * scale_y)
        right = round(114 * scale_x)
        bottom = round(110 * scale_y)
        width, height = right - left, bottom - top
        gap = max(1, round(3 * min(scale_x, scale_y)))
        count = min(len(self.img), max(1, int(max_pictures)), 4)

        layouts = {
            1: [(0, 0, width, height)],
            2: [
                (0, 0, (width - gap) // 2, height),
                ((width + gap) // 2, 0, width, height),
            ],
            3: [
                (0, 0, (width - gap) // 2, (height - gap) // 2),
                ((width + gap) // 2, 0, width, (height - gap) // 2),
                (0, (height + gap) // 2, width, height),
            ],
            4: [
                (0, 0, (width - gap) // 2, (height - gap) // 2),
                ((width + gap) // 2, 0, width, (height - gap) // 2),
                (0, (height + gap) // 2, (width - gap) // 2, height),
                ((width + gap) // 2, (height + gap) // 2, width, height),
            ],
        }

        content = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        for index, (x1, y1, x2, y2) in enumerate(layouts.get(count, [])):
            thumb = self.thumbnailize(
                self.img[index], x2 - x1, y2 - y1, crop=True
            )
            x = x1 + (x2 - x1 - thumb.size[0]) // 2
            y = y1 + (y2 - y1 - thumb.size[1]) // 2
            content.paste(thumb, (x, y), thumb)

        bg.alpha_composite(content, (left, top))
        fg = Image.open(fg_picture).convert("RGBA")
        bg.alpha_composite(fg)
        self.thumb = bg

    def save_thumb(self, output_path, output_format='PNG'):
        """ Save the thumbnail in a file.

        Argument:
          * output_path -- the output path for the thumbnail
        Keyword argument:
          * format -- the format of the picture (PNG, JPEG,...)

        NOTE : The output format must be a PNG for a standard
               freedesktop thumbnail
        """
        if self.thumb is not None:
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            self.thumb.save(output_path, output_format)
        else:
            print("E: [%s:Thumb.save_thumb] No thumbnail created" % __file__)


def is_supported_picture(filename):
    """Return whether filename has a supported image extension."""
    return os.path.splitext(filename)[1].lower() in PICTURES_EXT


def search_pictures(path):
    """Return up to four supported images directly inside path."""
    pictures = []
    for filename in sorted(os.listdir(path)):
        file_path = os.path.join(path, filename)
        if os.path.isfile(file_path) and is_supported_picture(filename):
            pictures.append(file_path)
            if len(pictures) >= 4:
                break
    return pictures


def search_pictures_recursiv(path):
    """Return up to four supported images found recursively inside path."""
    pictures = []
    for root, dirs, files in os.walk(path):
        dirs.sort()
        for filename in sorted(files):
            if is_supported_picture(filename):
                pictures.append(os.path.join(root, filename))
                if len(pictures) >= 4:
                    return pictures
    return pictures


def match_path(path, path_list):
    """ Test if a folder is a sub-folder of another one in the list.

    Arguments
      * path -- path to check
      * path_list -- list of path
    """
    match = False
    #We add a slash at the end.
    if path[-1:] != "/":
        path += "/"
    for entry in path_list:
        #We add a slash at the end.
        if entry[-1:] != "/":
            entry += "/"
        if re.match(r"^" + entry + ".*", path):
            if path != entry:
                match = True
                break
    return match


def gvfs_uri_to_path(uri):
    """Returns local file path from gvfs URI

    Arguments:
    uri -- the gvfs URI
    """
    if not re.match(r"^[a-zA-Z0-9_-]+://", uri):
        return uri
    gvfs = Gio.Vfs.get_default()
    return gvfs.get_file_for_uri(uri).get_path()


if __name__ == "__main__":
    # Input folder, output thumbnail and optional requested size.
    if len(sys.argv) in (3, 4):
        INPUT_FOLDER = gvfs_uri_to_path(sys.argv[1])
        OUTPUT_FILE = gvfs_uri_to_path(sys.argv[2])
        THUMBNAIL_SIZE = sys.argv[3] if len(sys.argv) == 4 else 128
    else:
        #Display informations and usage
        print("Nemo Folder Preview - %s" % __doc__)
        print("Version: %s" % __version__)
        print(__copyright__)
        sys.exit(1)

    #If input path does not exists
    if not os.path.isdir(INPUT_FOLDER):
        print("E: [%s:__main__] '%s' is not a directory" % (__file__, INPUT_FOLDER))
        sys.exit(2)

    #Load configuration
    CONF = Conf()
    prepare_picture_theme(CONF, THUMBNAIL_SIZE)

    #Ignored folders
    if match_path(INPUT_FOLDER, CONF['ignored_paths']) \
    and not match_path(INPUT_FOLDER, CONF['neverignored_paths']):
        sys.exit(0)

    #Folders whose name starts with a dot
    elif CONF['ignored_dotted'] and re.match(r".*/\..*", INPUT_FOLDER):
        sys.exit(0)

    # Picture folders
    elif CONF['pictures_enabled'] and match_path(INPUT_FOLDER, CONF['pictures_paths']):
        picture_list = search_pictures(INPUT_FOLDER)
        if not picture_list:
            picture_list = search_pictures_recursiv(INPUT_FOLDER)

        thumbnail = Thumb(picture_list)
        thumbnail.pictures_thumbnail(
                CONF['pictures_bg'],
                CONF['pictures_fg'],
                CONF['pictures_maxthumbs']
                )
        thumbnail.save_thumb(OUTPUT_FILE, "PNG")

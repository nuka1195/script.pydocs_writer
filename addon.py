#!/usr/bin/python
# -*- coding: utf-8 -*-
#
## PyDocs & PyPredefs Writer

import os
import pydoc
import resources.lib.pypredefcom as pypredefcomp
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON_ID = "script.pydocs_writer"


class Dialog(object):
    """
    Dialog Class:
    """
    def __init__(self):
        # get Addon object
        self.Addon = xbmcaddon.Addon(id=ADDON_ID)
        self.m_pDialog = None

    def __del__(self):
        # close dialog
        self.progress_dialog_close()

    def browse_dialog(self, type=3, heading="Choose", shares="files", mask="", useThumbs=False, treatAsFolder=False, default="", enableMultiple=False):
        """Show a browse dialog.

        keyword arguments:
        type           -- integer - the type of browse dialog (default 3)
        heading        -- string  - dialog heading (default "Choose")
        shares         -- string  - shares from sources.xml (default "files")
        mask           -- string  - '|' separated file mask (default "")
        useThumbs      -- boolean - enable autoswitch to thumb view if files exist (default False)
        treatAsFolder  -- boolean - enable playlists and archives to act as folders (default False)
        default        -- string  - default path or file (default "")
        enableMultiple -- boolean - enable multiple file selection (default False)

        Types:
          0 : ShowAndGetDirectory
          1 : ShowAndGetFile
          2 : ShowAndGetImage
          3 : ShowAndGetWriteableDirectory

        *Note, If enableMultiple is False (default): returns filename and/or path as a string
               to the location of the highlighted item, if user pressed 'Ok' or a masked item
               was selected. Returns the default value if dialog was canceled.
               If enableMultiple is True: returns tuple of marked filenames as a string
               if user pressed 'Ok' or a masked item was selected. Returns empty tuple if dialog was canceled.
               If type is 0 or 3 the enableMultiple parameter is ignore

        """
        # return user selection
        return xbmcgui.Dialog().browse(type, heading, shares, mask, useThumbs, treatAsFolder, default, enableMultiple)

    def progress_dialog_create(self):
        # create progress dialog
        self.m_pDialog = xbmcgui.DialogProgress()
        self.m_pDialog.create(self.Addon.getAddonInfo("Name"))

    def progress_dialog_update(self, count, module):
        # set message and update progress dialog
        msg = "{doc} - {module}{ext}".format(doc=self.m_Type, module=module, ext=self.m_Ext)
        self.m_pDialog.update(count * (100 / len(self.modules)),
            self.Addon.getLocalizedString(30711).format(msg=msg),
            self.Addon.getLocalizedString(30712).format(msg=os.path.split(self.path)[0]))

    def progress_dialog_cancelled(self):
        # did user cancel job
        return self.m_pDialog.iscanceled()

    def progress_dialog_close(self):
        # close progress dialog
        if (self.m_pDialog is not None):
            self.m_pDialog.close()


class Writer(Dialog):
    """Main writer class, handles user input and output."""
    def __init__(self, _type, _ext):
        # initialize Dialog class
        Dialog.__init__(self)
        # set type and extension
        self.m_Type = _type
        self.m_Ext = _ext

    # Abstract method, must be overridden
    def include(self):
        raise NotImplementedError("Subclass must implement abstract method (include)")

    # Abstract method, must be overridden
    def write_doc(self):
        raise NotImplementedError("Subclass must implement abstract method (write_doc)")

    def write_docs(self):
        # is user preference to include this type
        if (not self.include()): return
        # get user preferences
        doc_path = self._get_doc_path()
        # if a valid doc_path create docs
        if (doc_path):
            # create progress dialog
            self.progress_dialog_create()
            # modules
            self.modules = ["xbmc", "xbmcaddon", "xbmcgui", "xbmcplugin", "xbmcvfs"]
            # enumerate thru and write our help docs
            for count, module in enumerate(self.modules):
                # set correct path
                self.path = self._make_path(module, doc_path)
                # only need to write doc if we have a valid dir
                if (self.path is not None):
                    # update dialog
                    self.progress_dialog_update(count, module)
                    # write file
                    self.write_doc(module)
                    # raise error if user cancelled job
                    if (self.progress_dialog_cancelled()):
                        raise KeyboardInterrupt

    def _make_path(self, module, doc_path):
        # set correct path
        _path = xbmc.validatePath(xbmc.translatePath(os.path.join(doc_path, self.m_Type))).decode("UTF-8")
        try:
            # make dir if it doesn't exist
            if (not xbmcvfs.mkdirs(_path)):
                raise IOError(1, "Unable to make dir structure!", _path)
        except IOError as error:
            # oops
            xbmc.log("An error occurred making dir for {type}! ({error} - [{path}])".format(
                type=self.m_Type, error=error.strerror, path=error.filename), xbmc.LOGERROR)
            return None
        else:
            # return full filepath
            return os.path.join(_path, "{module}{ext}".format(module=module, ext=self.m_Ext))

    def _get_doc_path(self):
        # get users path location
        dp = self.Addon.getSetting("doc_path")
        # get location if none set
        if (not dp):
            # get location to save docs
            dp = self.browse_dialog(heading=self.Addon.getLocalizedString(30110))
            # save doc_path
            if (dp):
                self.Addon.setSetting("doc_path", dp)
            else:
                raise KeyboardInterrupt

        return dp

    def log_error(self, module, error):
        # log error
        xbmc.log("An error occurred saving {type} {module}{ext}! ({error})".format(
            type=self.m_Type, module=module, ext=self.m_Ext, error=error), xbmc.LOGERROR)


class PyDoc(Writer):
    """PyDoc Class: Subclass of Writer class to handle special write methods."""

    def __init__(self):
        # intialize Writer class
        Writer.__init__(self, "PyDocs", ".html")

    def include(self):
        # does user prefer pydocs
        return self.Addon.getSetting("include_pydocs") == "true"

    def write_doc(self, module):
        try:
            # get our file object
            f = open(self.path, "w")
            # write document
            f.write(pydoc.HTMLDoc().document(eval(module)))
        except IOError as error:
            # oops
            self.log_error(module, error.strerror)
        else:
            # close file
            f.close()


class PyPredef(Writer):
    """PyPredef Class: Subclass of Writer class to handle special write function."""

    def __init__(self):
        # intialize Writer class
        Writer.__init__(self, "PyPredefs", ".pypredef")

    def include(self):
        # does user prefer pypredefs
        return self.Addon.getSetting("include_pypredefs") == "true"

    def write_doc(self, module):
        try:
            # get our file object
            f = open(self.path, "w")
            # write document
            pypredefcomp.pypredefmodule(f, eval(module))
        except IOError as error:
            # oops
            self.log_error(module, error.strerror)
        else:
            # close file
            f.close()


if (__name__ == "__main__"):
    try:
        # write the documents
        PyDoc().write_docs()
        PyPredef().write_docs()
    except KeyboardInterrupt:
        pass

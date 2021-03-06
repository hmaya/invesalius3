#!/usr/bin/python
#--------------------------------------------------------------------------
# Software:     InVesalius - Software de Reconstrucao 3D de Imagens Medicas
# Copyright:    (C) 2001  Centro de Pesquisas Renato Archer
# Homepage:     http://www.softwarepublico.gov.br
# Contact:      invesalius@cti.gov.br
# License:      GNU - GPL 2 (LICENSE.txt/LICENCA.txt)
#--------------------------------------------------------------------------
#    Este programa e software livre; voce pode redistribui-lo e/ou
#    modifica-lo sob os termos da Licenca Publica Geral GNU, conforme
#    publicada pela Free Software Foundation; de acordo com a versao 2
#    da Licenca.
#
#    Este programa eh distribuido na expectativa de ser util, mas SEM
#    QUALQUER GARANTIA; sem mesmo a garantia implicita de
#    COMERCIALIZACAO ou de ADEQUACAO A QUALQUER PROPOSITO EM
#    PARTICULAR. Consulte a Licenca Publica Geral GNU para obter mais
#    detalhes.
#-------------------------------------------------------------------------


import multiprocessing
import optparse as op
import os
import sys
import shutil
import traceback
import ConfigParser
import re

if sys.platform == 'win32':
    import _winreg
else:
    if sys.platform != 'darwin':
        import wxversion
        #wxversion.ensureMinimal('2.8-unicode', optionsRequired=True)
        #wxversion.select('2.8-unicode', optionsRequired=True)
        wxversion.ensureMinimal('3.0')
        
import wx
#from wx.lib.pubsub import setupv1 #new wx
from wx.lib.pubsub import setuparg1# as psv1
#from wx.lib.pubsub import Publisher 
#import wx.lib.pubsub as ps
from wx.lib.pubsub import pub #as Publisher

#import wx.lib.agw.advancedsplash as agw
#if sys.platform == 'linux2':
#    _SplashScreen = agw.AdvancedSplash
#else:
#    if sys.platform != 'darwin':
#        _SplashScreen = wx.SplashScreen


import invesalius.gui.language_dialog as lang_dlg
import invesalius.i18n as i18n
import invesalius.session as ses
import invesalius.utils as utils

FS_ENCODE = sys.getfilesystemencoding()

if sys.platform == 'win32':
    from invesalius.expanduser import expand_user
    try:
        USER_DIR = expand_user()
    except:
        USER_DIR = os.path.expanduser('~').decode(FS_ENCODE)
else:
    USER_DIR = os.path.expanduser('~').decode(FS_ENCODE)

USER_INV_DIR = os.path.join(USER_DIR, u'.invesalius')
USER_PRESET_DIR = os.path.join(USER_INV_DIR, u'presets')
USER_RAYCASTING_PRESETS_DIRECTORY = os.path.join(USER_PRESET_DIR, u'raycasting')
USER_LOG_DIR = os.path.join(USER_INV_DIR, u'logs')

CONFIG_DIR = ''
# ------------------------------------------------------------------


class InVesalius(wx.App):
    """
    InVesalius wxPython application class.
    """
    def OnInit(self):
        """
        Initialize splash screen and main frame.
        """
        
        from multiprocessing import freeze_support
        freeze_support()

        self.SetAppName("InVesalius 3")
        self.splash = SplashScreen()
        self.splash.Show()
        wx.CallLater(1000,self.Startup2)

        return True

    def MacOpenFile(self, filename):
        """
        Open drag & drop files under darwin
        """
        path = os.path.abspath(filename)
        pub.sendMessage('Open project', pubsub_evt=path)

    def Startup2(self):
        self.control = self.splash.control
        self.frame = self.splash.main
        self.SetTopWindow(self.frame)
        self.frame.Show()
        self.frame.Raise()

# ------------------------------------------------------------------

class SplashScreen(wx.SplashScreen):
    """
    Splash screen to be shown in InVesalius initialization.
    """
    def __init__(self):
        # Splash screen image will depend on currently language
        lang = False

        self.locale = wx.Locale(wx.LANGUAGE_DEFAULT)

        # Language information is available in session configuration
        # file. First we need to check if this file exist, if now, it
        # should be created
        create_session = False
        session = ses.Session()
        if not (session.ReadSession()):
            create_session = True

        install_lang = 0
        # Check if there is a language set (if session file exists
        if session.ReadLanguage():
            lang = session.GetLanguage()
            if (lang != "False"):
                _ = i18n.InstallLanguage(lang)
                install_lang = 1
            else:
                install_lang = 0
        else:
            install_lang = 0

        # If no language is set into session file, show dialog so
        # user can select language
        if install_lang == 0:
            dialog = lang_dlg.LanguageDialog()

            # FIXME: This works ok in linux2, darwin and win32,
            # except on win64, due to wxWidgets bug
            try:
                ok = (dialog.ShowModal() == wx.ID_OK)
            except wx._core.PyAssertionError:
                ok = True
            finally:
                if ok:
                    lang = dialog.GetSelectedLanguage()
                    session.SetLanguage(lang)
                    _ = i18n.InstallLanguage(lang)
                else:
                    homedir = self.homedir = os.path.expanduser('~')
                    invdir = os.path.join(homedir, ".invesalius")
                    shutil.rmtree(invdir)
                    sys.exit()
                    
        # Session file should be created... So we set the recent
        # choosen language
        if (create_session):
            session.CreateItens()
            session.SetLanguage(lang)
            session.WriteSessionFile()

        session.SaveConfigFileBackup()

           
        # Only after language was defined, splash screen will be
        # shown
        if lang:
            #  print "LANG", lang, _, wx.Locale(), wx.GetLocale()
            import locale
            locale.setlocale(locale.LC_ALL, '')
            # For pt_BR, splash_pt.png should be used
            if (lang.startswith('pt')):
                icon_file = "splash_pt.png"
            else:
                icon_file = "splash_" + lang + ".png"

            if hasattr(sys,"frozen") and (sys.frozen == "windows_exe"\
                                        or sys.frozen == "console_exe"):
                abs_file_path = os.path.abspath(".." + os.sep)
                path = abs_file_path
                path = os.path.join(path, 'icons', icon_file)
            
            else:

                path = os.path.join(".","icons", icon_file)
                if not os.path.exists(path):
                    path = os.path.join(".", "icons", "splash_en.png")
				
            bmp = wx.Image(path).ConvertToBitmap()

            style = wx.SPLASH_TIMEOUT | wx.SPLASH_CENTRE_ON_SCREEN
            wx.SplashScreen.__init__(self,
                                     bitmap=bmp,
                                     splashStyle=style,
                                     milliseconds=1500,
                                     id=-1,
                                     parent=None)
            self.Bind(wx.EVT_CLOSE, self.OnClose)
            wx.Yield()
            wx.CallLater(200,self.Startup)

    def Startup(self):
        # Importing takes sometime, therefore it will be done
        # while splash is being shown
        from invesalius.gui.frame import Frame
        from invesalius.control import Controller
        from invesalius.project import Project
        
        self.main = Frame(None)
        self.control = Controller(self.main)
        
        self.fc = wx.FutureCall(1, self.ShowMain)
        options, args = parse_comand_line()
        wx.FutureCall(1, use_cmd_optargs, options, args)

        # Check for updates
        from threading import Thread
        p = Thread(target=utils.UpdateCheck, args=())
        p.start()

    def OnClose(self, evt):
        # Make sure the default handler runs too so this window gets
        # destroyed
        evt.Skip()
        self.Hide()

        # If the timer is still running then go ahead and show the
        # main frame now
        if self.fc.IsRunning():
            self.fc.Stop()
            self.ShowMain()

    def ShowMain(self):
        # Show main frame
        self.main.Show()

        if self.fc.IsRunning():
            self.Raise()


def non_gui_startup(options, args):
    lang = 'en'
    #_ = i18n.InstallLanguage(lang)

    from invesalius.control import Controller
    from invesalius.project import Project

    session = ses.Session()
    if not session.ReadSession():
        session.CreateItens()
        #session.SetLanguage(lang)
        session.WriteSessionFile()

    control = Controller(None)

    use_cmd_optargs(options, args)

# ------------------------------------------------------------------


def parse_comand_line():
    """
    Handle command line arguments.
    """
    session = ses.Session()


    # Parse command line arguments
    parser = op.OptionParser()

    parser.add_option("-c","--config",
                      action="store")

    # -d or --debug: print all pubsub messagessent
    parser.add_option("-d", "--debug",
                      action="store_true",
                      dest="debug")

    parser.add_option('--no-gui',
                      action='store_true',
                      dest='no_gui')

    # -i or --import: import DICOM directory
    # chooses largest series
    parser.add_option("-i", "--import",
                      action="store",
                      dest="dicom_dir")

    parser.add_option("--import-all",
                      action="store")

    parser.add_option("-s", "--save",
                      help="Save the project after an import.")

    parser.add_option("-t", "--threshold",
                      help="Define the threshold for the export (e.g. 100-780).")

    parser.add_option("-e", "--export",
                      help="Export to STL.")

    parser.add_option("-a", "--export-to-all",
                      help="Export to STL for all mask presets.")

    options, args = parser.parse_args()
    return options, args


def use_cmd_optargs(options, args):

    # If debug argument...
    if options.debug:
        pub.subscribe(print_events, pub.ALL_TOPICS)
        session = ses.Session()
        session.debug = 1

    # If import DICOM argument...
    if options.dicom_dir:
        import_dir = options.dicom_dir
        pub.sendMessage(('Import directory'), {'directory': import_dir, 'gui': not options.no_gui})

        if options.save:
            pub.sendMessage(('Save project'), os.path.abspath(options.save))
            exit(0)

        check_for_export(options)

        return True
    elif options.import_all:
        import invesalius.reader.dicom_reader as dcm
        uiModeValue = not options.no_gui
        for patient in dcm.GetDicomGroups(options.import_all):
            for group in patient.GetGroups():
                pub.sendMessage(('Import group'), {'group': group, 'gui': uiModeValue})
                check_for_export(options, suffix=group.title, remove_surfaces=False)
                pub.sendMessage(('Remove masks'), [0])
        return True

    # Check if there is a file path somewhere in what the user wrote
    # In case there is, try opening as it was a inv3
    else:
        for arg in reversed(args):
            file = arg.decode(sys.stdin.encoding)
            if os.path.isfile(file):
                path = os.path.abspath(file)
                pub.sendMessage('Open project', path)
                check_for_export(options)
                return True

            file = arg.decode(FS_ENCODE)
            if os.path.isfile(file):
                path = os.path.abspath(file)
                pub.sendMessage('Open project', path)
                check_for_export(options)
                return True

    return False


def sanitize(text):
    text = str(text).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', text)


def check_for_export(options, suffix='', remove_surfaces=False):
    suffix = sanitize(suffix)

    if options.export:
        if not options.threshold:
            print("Need option --threshold when using --export.")
            exit(1)
        threshold_range = tuple([int(n) for n in options.threshold.split(',')])

        if suffix:
            if options.export.endswith('.stl'):
                path_ = '{}-{}.stl'.format(options.export[:-4], suffix)
            else:
                path_ = '{}-{}.stl'.format(options.export, suffix)
        else:
            path_ = options.export

        export(path_, threshold_range, remove_surface=remove_surfaces)
    elif options.export_to_all:
        # noinspection PyBroadException
        try:
            from invesalius.project import Project

            for threshold_name, threshold_range in Project().presets.thresh_ct.iteritems():
                if isinstance(threshold_range[0], int):
                    path_ = u'{}-{}-{}.stl'.format(options.export_to_all, suffix, threshold_name)
                    export(path_, threshold_range, remove_surface=True)
        except:
            traceback.print_exc()
        finally:
            exit(0)


def export(path_, threshold_range, remove_surface=False):
    import invesalius.constants as const

    pub.sendMessage('Set threshold values', threshold_range)

    surface_options = {
        'method': {
            'algorithm': 'Default',
            'options': {},
        }, 'options': {
            'index': 0,
            'name': '',
            'quality': 'Optimal *',
            'fill': False,
            'keep_largest': False,
            'overwrite': False,
        }
    }
    pub.sendMessage(('Create surface from index'), surface_options)
    pub.sendMessage(('Export surface to file'), (path_, const.FILETYPE_STL))
    if remove_surface:
        pub.sendMessage(('Remove surfaces'), [0])


def print_events(data):
    """
    Print pubsub messages
    """
    utils.debug(data.topic)


def main():
    """
    Initialize InVesalius GUI
    """
    options, args = parse_comand_line()
    if options.config:
        CONFIG_DIR = options.config

    sys.path=['.', CONFIG_DIR+'app', 
                CONFIG_DIR+'Python27',
                CONFIG_DIR+'Python27\\DLLs',
                CONFIG_DIR+'Python27\\Lib',
                CONFIG_DIR+'Python27\\Lib\\site-packages',
                CONFIG_DIR+'Python27\Scripts',
                CONFIG_DIR+'Python27\\Lib\site-packages\gdcm',
                CONFIG_DIR+'Python27\\Lib\\site-packages\\python_ca_smoothing',
                CONFIG_DIR+'Python27\\Lib\\site-packages\\vtk',
                CONFIG_DIR+'Python27\\Lib\\site-packages\\wx-3.0-msw']

    config_file_path = CONFIG_DIR + 'config.ini'

    cf = ConfigParser.ConfigParser()
    cf.read(config_file_path)
    uiMode = cf.get("config", "uiMode")
    if uiMode == 'no-gui':
        options.no_gui = True

    importMode = cf.get("config", "importMode")
    inPath = cf.get("config", "inPath")
    if importMode == 'import-all':
        options.import_all = inPath

    threshold = cf.get("config", "threshold")
    options.threshold = threshold

    exportMode = cf.get("config", "exportMode")
    outPath = cf.get("config", "outPath")
    if exportMode=='export' :
        options.export = outPath
    
    if options.no_gui:
        non_gui_startup(options, args)
    else:
        application = InVesalius(0)
        application.MainLoop()

if __name__ == '__main__':
    #Is needed because of pyinstaller
    multiprocessing.freeze_support()

    #Needed in win 32 exe
    if hasattr(sys,"frozen") and sys.platform.startswith('win'):

        #Click in the .inv3 file support
        root = _winreg.HKEY_CLASSES_ROOT
        key = "InVesalius 3.1\InstallationDir"
        hKey = _winreg.OpenKey (root, key, 0, _winreg.KEY_READ)
        value, type_ = _winreg.QueryValueEx (hKey, "")
        path = os.path.join(value,'dist')

        os.chdir(path)

    # Create raycasting presets' folder, if it doens't exist
    if not os.path.isdir(USER_RAYCASTING_PRESETS_DIRECTORY):
        os.makedirs(USER_RAYCASTING_PRESETS_DIRECTORY)

    # Create logs' folder, if it doesn't exist
    if not os.path.isdir(USER_LOG_DIR):
        os.makedirs(USER_LOG_DIR)

    if hasattr(sys,"frozen") and sys.frozen == "windows_exe":
        # Set system standard error output to file
        path = os.path.join(USER_LOG_DIR, u"stderr.log")
        sys.stderr = open(path, "w")

    # Add current directory to PYTHONPATH, so other classes can
    # import modules as they were on root invesalius folder
    sys.path.insert(0, '.')
    sys.path.append(".")


    # Init application
    main()


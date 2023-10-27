# 更改OCR语言
from ui.widget import Widget  # 控件
from utils.config import Config
from utils.asset import Asset  # 资源
from utils.data_structure import KeyList
from utils.hotkey import Hotkey
from utils.logger import GetLog

import tkinter as tk
from tkinter import ttk

Log = GetLog()


class OcrLanguageWin:
    def __init__(self):
        self.lanList = KeyList()
        self.win = None

    def _initWin(self):
        # Main window
        self.win = tk.Toplevel()
        self.win.iconphoto(False, Asset.getImgTK('umiocr24')) # Set the window icon
        self.win.minsize(250, 340) # Minimum size
        self.win.geometry(f'{250}x{340}')
        self.win.unbind('<MouseWheel>')
        self.win.title('Change language')
        self.win.wm_protocol( # Register window closing event
            'WM_DELETE_WINDOW', self.exit)
        fmain = tk.Frame(self.win, padx=4, pady=4)
        fmain.pack(fill='both', expand=True)

        # topInformation
        ftop = tk.Frame(fmain)
        ftop.pack(side='top', fill='x')
        tk.Label(ftop, text='Current:').pack(side='left')
        tk.Label(ftop, textvariable=Config.getTK(
            'ocrConfigName')).pack(side='left')
        wid = tk.Label(ftop, text='prompt', fg='deeppink', cursor='question_arrow')
        wid.pack(side='right')
        Config.main.balloon.bind(
            wid, '''Window operations:
1. When normal, switching language takes effect immediately
2. If you switch the language during the mission, it will take effect on the next mission.
3. After enabling/canceling the pin on top of the main window, you need to reopen this window to set the window to the corresponding pin on top status.

More languages:
This software has organized multi-language expansion packages, which can import more language model libraries. OK
Manually import the PaddleOCR compatible model library. For details, please visit the project Github homepage. ''')

        # central control
        fmiddle = tk.Frame(fmain, pady=4)
        fmiddle.pack(side='top', expand=True, fill='both')
        fmiddle.grid_columnconfigure(0, weight=1)

        # Language table
        ftable = tk.Frame(fmiddle, bg='red')
        ftable.pack(side='left', expand=True, fill='both')
        self.table = ttk.Treeview(
            master=ftable, # Parent container
            # height=50, # Number of rows displayed in the table, height rows
            columns=['ConfigName'], # Displayed columns
            show='headings', # Hide the first column
        )
        self.table.pack(expand=True, side='left', fill='both')
        self.table.heading('ConfigName', text='Language')
        self.table.column('ConfigName', minwidth=40)
        vbar = tk.Scrollbar( # Bind scroll bar
            ftable, orient='vertical', command=self.table.yview)
        vbar.pack(side='left', fill='y')
        self.table["yscrollcommand"] = vbar.set
        self.table.bind('<ButtonRelease-1>', # Release the bound mouse. When pressed, let the table component update first, and then release to get the latest value.
                        lambda *e: self.updateLanguage())

        # fmright = tk.Frame(fmiddle)
        # fmright.pack(side='left', fill='y')
        # tk.Label(fmright, text='右侧').pack(side='left')

        # Bottom control
        fbottom = tk.Frame(fmain)
        fbottom.pack(side='top', fill='x')
        Widget.comboboxFrame(fbottom, 'Combined paragraphs:', 'tbpu').pack(
            side='top', fill='x', pady=3)
        wid = ttk.Checkbutton(fbottom, variable=Config.getTK('isLanguageWinAutoOcr'),
                              text='Read pictures immediately')
        wid.pack(side='left')
        Config.main.balloon.bind(wid, 'After changing the language, immediately perform a clipboard recognition in the current language')
        wid = ttk.Button(fbottom, text='Close', width=5,
                         command=self.exit)
        wid.pack(side='right')
        wid = ttk.Checkbutton(fbottom, variable=Config.getTK('isLanguageWinAutoExit'),
                              text='Automatically close')
        wid.pack(side='right', padx=10)
        Config.main.balloon.bind(wid, 'After changing the language, close this window immediately')

        self.updateTable()

    def open(self):
        if self.win:
            self.win.state('normal') #Restore the foreground state
        else:
            self._initWin() #Initialize window
        self.win.attributes('-topmost', 1) # Set the top level
        if Config.get('isWindowTop'):
            self.win.title('Change language (top)')
        else:
            self.win.title('Change language')
            self.win.attributes('-topmost', 0) #Remove
        #Move the window near the mouse
        (x, y) = Hotkey.getMousePos()
        w = self.win.winfo_width()
        h = self.win.winfo_height()
        if w < 2:
            w = 250
        if h < 2:
            h = 340
        w1 = self.win.winfo_screenwidth()
        h1 = self.win.winfo_screenheight()
        x -= round(w/2)
        y -= 140
        # preventWindowFromExtendingBeyondScreen
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > w1-w:
            x = w1-w
        if y > h1-h-70:
            y = h1-h-70
        self.win.geometry(f"+{x}+{y}")

    def updateTable(self):  # Refresh language table
        configDist = Config.get('ocrConfig')
        configName = Config.get('ocrConfigName')
        for key, value in configDist.items():
            tableInfo = (key)
            dictInfo = {'key': key}
            id = self.table.insert('', 'end', values=tableInfo) # Add to table component
            self.lanList.append(id, dictInfo)
            if key == configName:
                self.table.selection_set(id)

    def updateLanguage(self):  # Refresh the selected language and write the configuration
        chi = self.table.selection()
        if len(chi) == 0:
            return
        chi = chi[0]
        lan = self.lanList.get(key=chi)['key']
        Config.set('ocrConfigName', lan)
        if Config.get('isLanguageWinAutoExit'): # Automatically close
            self.exit()
        if Config.get('isLanguageWinAutoOcr'): # Repeat the task
            Config.main.runClipboard()

    def exit(self):
        self.win.withdraw()  # hideWindow


lanWin = OcrLanguageWin()


def ChangeOcrLanguage():
    lanWin.open()

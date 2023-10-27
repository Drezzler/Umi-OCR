from utils.config import Config, Umi, ScsModeFlag, WindowTopModeFlag  # Load configuration first
from utils.logger import GetLog
from utils.asset import *  # resources
from utils.data_structure import KeyList
from utils.tool import Tool
from utils.startup import Startup  # Startup method
from utils.hotkey import Hotkey  # Shortcut key
from utils.command_arg import Parse, Mission  # Start parameter analysis
from ui.win_notify import Notify  # Notification pop-up window
from ui.win_screenshot import ScreenshotCopy  # Screenshot
from ui.win_select_area import IgnoreAreaWin  # Child window
from ui.win_ocr_language import ChangeOcrLanguage  # Change language
from ui.widget import Widget  # Control
from ui.pmw.PmwBalloon import Balloon  # Bubble prompt
from ui.tray import SysTray
from ocr.engine import OCRe, MsnFlag, EngFlag  # Engine
# Image recognition task processor
from ocr.msn_batch_paths import MsnBatch
from ocr.msn_quick import MsnQuick
import os
import ctypes
from sys import argv
from PIL import Image  # image
import tkinter as tk
import tkinter.font
import tkinter.filedialog
import tkinter.colorchooser
from tkinter import ttk
from windnd import hook_dropfiles  # File drag and drop
from webbrowser import open as webOpen  # "About" panel opens the project URL
from argparse import ArgumentParser  # Startup parameters

Log = GetLog()


class MainWin:
    def __init__(self):
        self.batList = KeyList()  # Manage batch image information and list of table IDs
        self.tableKeyList = []  # Store self.imgDict in order
        self.lockWidget = []  # Components that require runtime locking

        # 1.Initialize the main window
        self.win = tk.Tk()
        self.win.withdraw()  # Hide the window and wait until initialization is completed before considering whether to display it.
        self.balloon = Balloon(self.win)  # Bubble box

        def initStyle():  # 初始化样式
            style = ttk.Style()
            # winnative clam alt default classic vista xpnative
            # style.theme_use('default')
            style.configure('icon.TButton', padding=(12, 0))
            style.configure('go.TButton', font=('Microsoft YaHei', '12', ''),  # bold
                            width=9)
            style.configure('gray.TCheckbutton', foreground='gray')

        initStyle()

        def initDPI():
            # Call the api set to be scaled by the application
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            # Call the api to get the current scaling factor
            ScaleFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
            # Set scaling factor
            self.win.tk.call('tk', 'scaling', ScaleFactor / 100)

        # initDPI()

        def initWin():
            self.win.title(Umi.name)
            # Window size and position
            w, h = 360, 500 # Initial size and minimum size of the window
            ws, hs = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
            x, y = round(ws / 2 - w / 2), round(hs / 2 - h / 2) #Initial position, center of the screen
            self.win.minsize(w, h) # Minimum size
            self.win.geometry(f"{w}x{h}+{x}+{y}") #Initial size and position
            self.win.protocol("WM_DELETE_WINDOW", self.onClose) # Window closes
            # Drag the registration file and it will be valid in the entire main window.
            # Change it to take effect after a period of delay to reduce the probability of exceptions.
            # Fatal Python error: PyEval_RestoreThread: NULL tstate
            # hook_dropfiles(self.win, func=self.draggedImages)
            hook_dropfiles(self.win, func=lambda e: self.win.after(
                80, lambda: self.draggedImages(e)))
            # icon
            Asset.initRelease() # Release base64 resources to local
            Asset.initTK() #Initialize tk picture
            self.win.iconphoto(False, Asset.getImgTK('umiocr24')) # Set the window icon

        initWin()

       # 2. Initialize configuration items
        self.win.bind('<<QuitEvent>>', lambda *e: self.onClose()) # Exit event
        Config.initTK(self) #Initialization settings
        Config.load() #Load local files
        Config.checkMultiOpen() # Check multi-open

        # 3.初始化组件
        def initTop():  # TOP BUTTON
            tk.Frame(self.win, height=5).pack(side='top')
            fr = tk.Frame(self.win)
            fr.pack(side='top', fill="x", padx=5)
            # 右侧按钮
            self.btnRun = ttk.Button(fr, command=self.run, text='Start task',
                                     style='go.TButton')
            self.btnRun.pack(side='right', fill='y')
            # Left text and progress bar
            vFrame2 = tk.Frame(fr)
            vFrame2.pack(side='top', fill='x')
            # ABOVE THE PROGRESS BAR
            wid = ttk.Checkbutton(vFrame2, variable=Config.getTK('isWindowTop'),
                                  text='Window on top', style='gray.TCheckbutton')
            wid.pack(side='left')
            self.balloon.bind(
                wid,
                'The window is locked to the top of the system\n\nWhen enabled, the mouseover prompt box in the software will be hidden')
            tk.Label(vFrame2, textvariable=Config.getTK('tipsTop2')).pack(
                side='right', padx=2)
            tk.Label(vFrame2, textvariable=Config.getTK('tipsTop1')).pack(
                side='right', padx=2)
            self.progressbar = ttk.Progressbar(fr)
            self.progressbar.pack(side='top', padx=2, pady=2, fill="x")

        initTop()

        self.notebook = ttk.Notebook(self.win)  # Initialize the tab component
        self.notebook.pack(expand=True, fill=tk.BOTH)  # 填满父组件
        self.notebookTab = []

        def initTab1():  # 表格卡
            tabFrameTable = tk.Frame(self.notebook)  # 选项卡主容器
            self.notebookTab.append(tabFrameTable)
            self.notebook.add(tabFrameTable, text=f'{"Batch processing": ^10s}')
            # 顶栏
            fr1 = tk.Frame(tabFrameTable)
            fr1.pack(side='top', fill='x', padx=1, pady=1)
            # 左
            btn = ttk.Button(fr1, image=Asset.getImgTK('screenshot24'),  # 截图按钮
                             command=self.openScreenshot,
                             style='icon.TButton', takefocus=0, )
            self.balloon.bind(
                btn,
                'Screenshot Description\nLeft-click drag: frame selection area\nRight click: Cancel box selection\n　　 Esc：Exit screenshot')
            btn.pack(side='left')
            self.lockWidget.append(btn)
            btn = ttk.Button(fr1, image=Asset.getImgTK('paste24'),  # 剪贴板按钮
                             command=self.runClipboard,
                             style='icon.TButton', takefocus=0, )
            self.balloon.bind(btn, 'Paste picture')
            btn.pack(side='left')
            self.lockWidget.append(btn)
            btn = ttk.Button(fr1, image=Asset.getImgTK('language24'),  # 语言按钮
                             command=ChangeOcrLanguage,
                             style='icon.TButton', takefocus=0)
            self.balloon.bind(btn, 'Change OCR language')
            btn.pack(side='left')
            self.lockWidget.append(btn)
            # 右
            btn = ttk.Button(fr1, image=Asset.getImgTK('clear24'),  # 清空按钮
                             command=self.clearTable,
                             style='icon.TButton', takefocus=0, )
            self.balloon.bind(btn, 'Clear form')
            btn.pack(side='right')
            self.lockWidget.append(btn)
            btn = ttk.Button(fr1, image=Asset.getImgTK('delete24'),  # 删除按钮
                             command=self.delImgList,
                             style='icon.TButton', takefocus=0, )
            self.balloon.bind(btn, 'Remove selected files\nHold down Shift or Ctrl，Left-click to select multiple files')
            btn.pack(side='right')
            self.lockWidget.append(btn)
            btn = ttk.Button(fr1, image=Asset.getImgTK('openfile24'),  # 打开文件按钮
                             command=self.openFileWin,
                             style='icon.TButton', takefocus=0, )
            self.balloon.bind(btn, 'Browse documents')
            btn.pack(side='right')
            self.lockWidget.append(btn)
            # 表格主体
            fr2 = tk.Frame(tabFrameTable)
            fr2.pack(side='top', fill='both')
            self.table = ttk.Treeview(
                master=fr2,  # 父容器
                height=50,  # 表格显示的行数,height行
                columns=['name', 'time', 'score'],  # 显示的列
                show='headings',  # 隐藏首列
            )
            self.table.pack(expand=True, side="left", fill='both')
            self.table.heading('name', text='FILE NAME')
            self.table.heading('time', text='TIME CONSUMING')
            self.table.heading('score', text='CONFIDENCE')
            self.table.column('name', minwidth=40)
            self.table.column('time', width=20, minwidth=20)
            self.table.column('score', width=30, minwidth=30)
            vbar = tk.Scrollbar(  # 绑定滚动条
                fr2, orient='vertical', command=self.table.yview)
            vbar.pack(side="left", fill='y')
            self.table["yscrollcommand"] = vbar.set

        initTab1()

        def initTab2():  # 输出卡
            tabFrameOutput = tk.Frame(self.notebook)  # 选项卡主容器
            self.notebookTab.append(tabFrameOutput)
            self.notebook.add(tabFrameOutput, text=f'{"Identify content": ^10s}')
            fr1 = tk.Frame(tabFrameOutput)
            fr1.pack(side='top', fill='x', padx=1, pady=1)
            self.isAutoRoll = tk.IntVar()
            self.isAutoRoll.set(1)
            # 左
            btn = ttk.Button(fr1, image=Asset.getImgTK('screenshot24'),  # 截图按钮
                             command=self.openScreenshot,
                             style='icon.TButton', takefocus=0, )
            self.balloon.bind(
                btn,
                'Screenshot Description\nLeft-click drag: frame selection area\nRight click: Cancel box selection\n　　 Esc：Exit screenshot')
            btn.pack(side='left')
            self.lockWidget.append(btn)
            btn = ttk.Button(fr1, image=Asset.getImgTK('paste24'),  # 剪贴板按钮
                             command=self.runClipboard,
                             style='icon.TButton', takefocus=0, )
            self.balloon.bind(btn, 'Paste picture')
            btn.pack(side='left')
            self.lockWidget.append(btn)
            btn = ttk.Button(fr1, image=Asset.getImgTK('language24'),  # 语言按钮
                             command=ChangeOcrLanguage,
                             style='icon.TButton', takefocus=0)
            self.balloon.bind(btn, 'Change OCR language')
            btn.pack(side='left')
            self.lockWidget.append(btn)

            # 右
            btn = ttk.Button(fr1, image=Asset.getImgTK('clear24'),  # 清空按钮
                             command=self.panelClear,
                             style='icon.TButton', takefocus=0, )
            self.balloon.bind(btn,
                              'Clear the output panel\nYou can enable automatic clearing of the panel in [Settings → Quick Picture Recognition]')
            btn.pack(side='right')

            ttk.Checkbutton(fr1, variable=self.isAutoRoll, text="AUTOSCROLL",
                            takefocus=0, ).pack(side='right')
            tf = tk.Label(fr1, text='STYLE OF CALLIGRAPHY', fg='gray', cursor='hand2')
            tf.pack(side='right', padx=10)
            tf.bind(
                '<Button-1>', lambda *e: self.notebook.select(self.notebookTab[2]))  # 转到设置卡
            self.balloon.bind(tf, 'Change the font of the output panel in the [Settings] tab')

            fr2 = tk.Frame(tabFrameOutput)
            fr2.pack(side='top', fill='both')
            vbar = tk.Scrollbar(fr2, orient='vertical')  # 滚动条
            vbar.pack(side="right", fill='y')
            self.textOutput = tk.Text(fr2, height=500, width=500)
            self.textOutput.pack(fill='both', side="left")
            self.textOutput.tag_config(  # 添加高亮标签
                'blue', foreground='blue')
            self.textOutput.tag_config(  # 添加高亮标签
                'red', foreground='red')
            vbar["command"] = self.textOutput.yview
            self.textOutput["yscrollcommand"] = vbar.set

        initTab2()

        def initTab3():  # 设置卡
            tabFrameConfig = tk.Frame(self.notebook)  # 选项卡主容器
            self.notebookTab.append(tabFrameConfig)
            self.notebook.add(tabFrameConfig, text=f'{"Set up": ^10s}')

            def initOptFrame():  # 初始化可滚动画布 及 内嵌框架
                optVbar = tk.Scrollbar(
                    tabFrameConfig, orient="vertical") # Create a scroll bar
                optVbar.pack(side="right", fill="y")
                self.optCanvas = tk.Canvas(
                    tabFrameConfig, highlightthickness=0) # Create a canvas to host the frame. highlightthicknessCancel highlight border
                self.optCanvas.pack(side="left", fill="both",
                                    expand="yes") # Fill the parent window
                self.optCanvas["yscrollcommand"] = optVbar.set # Bind scroll bar
                optVbar["command"] = self.optCanvas.yview
                self.optFrame = tk.Frame(self.optCanvas) # The frame that holds the setting items
                self.optFrame.pack()
                self.optCanvas.create_window( # Frame inserted into canvas
                    (0, 0), window=self.optFrame, anchor="nw")

            initOptFrame()

            LabelFramePadY = 3  # 每个区域上下间距

            def initTopTips():  # 顶部提示
                fTips = tk.Frame(self.optFrame)
                fTips.pack(side='top')
                tipsLab = tk.Label(
                    fTips, fg='red',
                    text='Close the window and pin it to the top to display the mouseover prompt box')
                if Config.get('isWindowTop'):
                    tipsLab.pack(side='top')
                tk.Frame(fTips).pack(side='top')  # 空框架，用于自动调整高度的占位

                def changeIsWinTop():
                    if Config.get('isWindowTop'):  # 启用置顶
                        tipsLab.pack(side='top')
                    else:  # 取消置顶
                        tipsLab.pack_forget()
                    self.gotoTop()

                Config.addTrace('isWindowTop', changeIsWinTop)

            initTopTips()

            def initSoftwareFrame():  # 软件行为设置
                fSoft = tk.LabelFrame(
                    self.optFrame, text='General settings')
                fSoft.pack(side='top', fill='x',
                           ipady=2, pady=LabelFramePadY, padx=4)

                # Main panel font settings
                fr3 = tk.Frame(fSoft)
                fr3.pack(side='top', fill='x', pady=2, padx=5)
                fr3.grid_columnconfigure(1, weight=1)
                self.balloon.bind(fr3, 'Adjust the font style of the output panel in the [Recognize Content] tab')
                tk.Label(fr3, text='Output panel font').grid(column=0, row=0, sticky='w')
                ff = tk.font.families()  # Get system font
                fontFamilies = []
                fontFamiliesABC = []
                for i in ff:
                    if not i[0] == '@':  # 排除竖版
                        if '\u4e00' <= i[0] <= '\u9fff':  # Those starting with Chinese are given priority
                            fontFamilies.append(i)
                        else:
                            fontFamiliesABC.append(i)
                fontFamilies += fontFamiliesABC
                cbox = ttk.Combobox(fr3, state='readonly', takefocus=0,
                                    textvariable=Config.getTK('textpanelFontFamily'), value=fontFamilies)
                cbox.grid(column=1, row=0, sticky='ew')
                self.balloon.bind(cbox,
                                  'Do not use the roller.\nPlease use the up and down arrow keys or pull the scroll bar to browse the list')
                tk.Label(fr3, text='SIZE').grid(column=2, row=0, sticky='w')
                tk.Entry(fr3, textvariable=Config.getTK('textpanelFontSize'),
                         width=4, takefocus=0).grid(column=3, row=0, sticky='w')
                tk.Label(fr3, text=' ').grid(column=4, row=0, sticky='w')
                ttk.Checkbutton(fr3, text='BOLD',
                                variable=Config.getTK('isTextpanelFontBold')).grid(column=5, row=0, sticky='w')
                # Check if the currently configured font exists
                f = Config.get('textpanelFontFamily')
                if f and f not in fontFamilies:
                    Log.error(f'Configure output panel font【{f}】does not exist. reset to empty')
                    Config.set('textpanelFontFamily', '')

                def updateTextpanel():
                    f = Config.get('textpanelFontFamily')
                    s = Config.get('textpanelFontSize')
                    b = Config.get('isTextpanelFontBold')
                    font = (f, s, 'bold' if b else 'normal')
                    self.textOutput['font'] = font

                Config.addTrace('textpanelFontFamily', updateTextpanel)
                Config.addTrace('textpanelFontSize', updateTextpanel)
                Config.addTrace('isTextpanelFontBold', updateTextpanel)
                updateTextpanel()

                fr1 = tk.Frame(fSoft)
                fr1.pack(side='top', fill='x', pady=2, padx=5)
                fr1.grid_columnconfigure(1, weight=1)
                self.balloon.bind(
                    fr1,
                    'You can close/open the system tray icon and modify the function triggered when double-clicking the icon\nAfter the item is modified, the next time you open the software takes effect')
                wid = ttk.Checkbutton(fr1, text='Displays the system tray icon',
                                      variable=Config.getTK('isTray'))
                wid.grid(column=0, row=0, sticky='w')
                Widget.comboboxFrame(fr1, '，Double-click the icon', 'clickTrayMode', width=12).grid(
                    column=1, row=0, sticky='w')

                fr2 = tk.Frame(fSoft)
                fr2.pack(side='top', fill='x', pady=2, padx=5)
                tk.Label(fr2, text='The main window closes：').pack(side='left', padx=2)
                ttk.Radiobutton(fr2, text='Quit the software',
                                variable=Config.getTK('isBackground'), value=False).pack(side='left')
                wid = ttk.Radiobutton(fr2, text='Minimize to tray',
                                      variable=Config.getTK('isBackground'), value=True)
                wid.pack(side='left', padx=15)
                self.balloon.bind(wid, 'This option is only valid when the system tray icon is displayed')

                # 弹出方式设置
                fr3 = tk.Frame(fSoft)
                fr3.pack(side='top', fill='x', pady=2, padx=5)
                tk.Label(fr3, text='The main window pops up：').pack(side='left', padx=2)
                wid = ttk.Radiobutton(fr3, text='Automatic ejection',
                                      variable=Config.getTK('WindowTopMode'), value=WindowTopModeFlag.finish)
                wid.pack(side='left')
                self.balloon.bind(
                    wid, 'The main window pops up when a quick image is recognized, or when a batch task is completed')
                wid = ttk.Radiobutton(fr3, text='静默模式',
                                      variable=Config.getTK('WindowTopMode'), value=WindowTopModeFlag.never)
                wid.pack(side='left', padx=15)
                self.balloon.bind(
                    wid, 'No proactive pop-ups\nSuggestions to enable notification pop-ups')

                # 消息弹窗设置
                def changeNotify():
                    if Config.get('isNotify'):
                        Notify('Welcome to Umi-OCR', 'Notification pop-up open')

                Config.addTrace('isNotify', changeNotify)
                fr4 = tk.Frame(fSoft)
                fr4.pack(side='top', fill='x', pady=2, padx=5)
                ttk.Checkbutton(
                    fr4, variable=Config.getTK('isNotify'), text='Enable notification popup').pack(side='left')

                # Start mode setting
                fr5 = tk.Frame(fSoft)
                fr5.pack(side='top', fill='x', pady=2, padx=5)
                self.balloon.bind(
                    fr5, 'can be set to silent startup, stored in the system tray, do not display the main window')
                ttk.Checkbutton(fr5, variable=Config.getTK('isAutoStartup'),
                                text='boot auto-start', command=Startup.switchAutoStartup).pack(side='left')
                ttk.Checkbutton(fr5, variable=Config.getTK('isStartMenu'),
                                text='Start Menu Item', command=Startup.switchStartMenu).pack(side='left', padx=20)
                ttk.Checkbutton(fr5, variable=Config.getTK('isDesktop'),
                                text='desktop shortcut', command=Startup.switchDesktop).pack(side='left')

            initSoftwareFrame()

            def quickOCR():  # quickImageRecognitionSettings
                fQuick = tk.LabelFrame(
                    self.optFrame, text='Quick image recognition')
                fQuick.pack(side='top', fill='x',
                            ipady=2, pady=LabelFramePadY, padx=4)
                # When the screenshot shortcut key is triggered, the child thread sends an event to the main thread to start the screenshot window in the main thread
                # Avoid window flickering caused by child threads directly evoking the screenshot window
                self.win.bind('<<ScreenshotEvent>>',
                              self.openScreenshot)  # 绑定截图事件
                cbox = Widget.comboboxFrame(fQuick, '截图模块：', 'scsMode')
                cbox.pack(side='top', fill='x', padx=4)
                self.balloon.bind(
                    cbox,
                    'Switching screenshot work module\n\n[Umi-OCR software screenshot] is convenient and accurate\n[Windows system screenshot] has better compatibility')
                frss = tk.Frame(fQuick)
                frss.pack(side='top', fill='x')
                fhkUmi = tk.Frame(frss)
                fhkUmi.pack(side='top', fill='x')
                fhkU0 = tk.Frame(fhkUmi)
                fhkU0.pack(side='top', fill='x', pady=2)
                tk.Label(fhkU0, text='指示器颜色：').pack(side='left')
                self.balloon.bind(fhkU0,
                                  'Modify the color of the indicator when taking a screenshot\nAfter the item is modified, the next time you open the software to take effect')

                def changeColor(configName, title=None):
                    initColor = Config.get(configName)
                    color = tk.colorchooser.askcolor(
                        color=initColor, title=title)
                    if color[1]:
                        Config.set(configName, color[1])

                lab1 = tk.Label(fhkU0, text='crosshair', cursor='hand2', fg='blue')
                lab1.pack(side='left', padx=9)
                lab1.bind(
                    '<Button-1>', lambda *e: changeColor('scsColorLine', 'Screenshot crosshair color'))
                lab2 = tk.Label(fhkU0, text='dotted box surface', cursor='hand2', fg='blue')
                lab2.pack(side='left', padx=9)
                lab2.bind(
                    '<Button-1>', lambda *e: changeColor('scsColorBoxUp', 'Screenshot rectangular box dashed line surface color'))
                lab3 = tk.Label(fhkU0, text='bottom of dotted box', cursor='hand2', fg='blue')
                lab3.pack(side='left', padx=9)
                lab3.bind(
                    '<Button-1>', lambda *e: changeColor('scsColorBoxDown', 'Screenshot rectangular box dotted bottom color'))
                wid = Widget.hotkeyFrame(fhkUmi, 'Screenshot recognition shortcut key', 'Screenshot',
                                         lambda *e: self.win.event_generate(
                                             '<<ScreenshotEvent>>'), isAutoBind=False)
                wid.pack(side='top', fill='x')
                self.balloon.bind(
                    wid,
                    'After turning off the shortcut key, you can still call the screenshot through the button on the panel or the small icon in the tray\nClick [Modify] to set a custom shortcut key')

                syssscom = 'win+shift+s'
                fhkSys = Widget.hotkeyFrame(frss, 'System screenshot shortcut key', 'Screenshot',
                                            lambda *e: self.win.event_generate(
                                                '<<ScreenshotEvent>>'), True, syssscom, isAutoBind=False)
                self.balloon.bind(
                    fhkSys,
                    'Call OCR after listening to the system screenshot\n\nIf the software does not respond after taking a screenshot, please make sure that the Windows system comes with it\nThe Auto Copy to Clipboard switch in Screenshots & Sketches is turned on')

                wid = Widget.hotkeyFrame(
                    fQuick, 'Paste picture shortcut key', 'Clipboard', self.runClipboard, isAutoBind=True)
                wid.pack(side='top', fill='x', padx=4)
                self.balloon.bind(wid, 'Try to read the clipboard, if there is an image, call OCR\nClick [Modify] to set a custom shortcut key')
                if Config.get('isAdvanced'): # Hide advanced options: key combination judgment adjustment
                    fr1 = tk.Frame(fQuick)
                    fr1.pack(side='top', fill='x', pady=2, padx=5)
                    tk.Label(fr1, text='Key combination: ').pack(side='left')
                    fr11 = tk.Frame(fr1)
                    fr11.pack(side='left')
                    self.balloon.bind(
                        fr11,
                        'Loose: As long as the currently pressed key contains the set key combination, it can be triggered\nStrict: The currently pressed key must be consistent with the set combination to trigger')
                    tk.Label(fr11, text='Trigger judgment').pack(side='left')
                    ttk.Radiobutton(fr11, text='loose',
                                    variable=Config.getTK('isHotkeyStrict'), value=False).pack(side='left')
                    ttk.Radiobutton(fr11, text='strict',
                                    variable=Config.getTK('isHotkeyStrict'), value=True).pack(side='left')
                    fr12 = tk.Frame(fr1)
                    fr12.pack(side='left')
                    self.balloon.bind(fr12, 'All keys in the combination must be pressed continuously within this time\n to trigger')
                    tk.Label(fr12, text=', time limit').pack(side='left')
                    tk.Entry(fr12,
                             textvariable=Config.getTK('hotkeyMaxTtl'), width=4).pack(side='left')
                    tk.Label(fr12, text='second').pack(side='left')

                fr2 = tk.Frame(fQuick)
                fr2.pack(side='top', fill='x', pady=2, padx=5)
                fr2.grid_columnconfigure(1, minsize=20)
                wid = ttk.Checkbutton(fr2, variable=Config.getTK('isScreenshotHideWindow'),
                                      text='Hide main window')
                wid.grid(column=0, row=0, sticky='w')
                self.balloon.bind(
                    wid, f'Hide the main window before taking a screenshot\nIt will delay {Config.get("screenshotHideWindowWaitTime")} milliseconds to wait for the window animation')
                wid = ttk.Checkbutton(fr2, variable=Config.getTK('isShowImage'),
                                      text='Screenshot preview window')
                wid.grid(column=2, row=0)
                self.balloon.bind(
                    wid, f'Unchecked: OCR image recognition immediately after taking a screenshot\nChecked: Display the image after taking a screenshot, you can recognize or save the image later')
                wid = ttk.Checkbutton(fr2, variable=Config.getTK('isNeedCopy'),
                                      text='Automatically copy results')
                wid.grid(column=0, row=1)
                self.balloon.bind(wid, 'After the quick image recognition is completed, copy the obtained text to the clipboard')
                wid = ttk.Checkbutton(fr2, variable=Config.getTK('isNeedClear'),
                                      text='Automatically clear the panel')
                wid.grid(column=2, row=1)
                self.balloon.bind(wid, f'Each quick image recognition will clear the recognition content panel and omit time and other information')

                if Config.get('isAdvanced'): # Hide advanced options: screenshot linkage
                    frSend = tk.Frame(fQuick)
                    frSend.pack(side='top', fill='x', pady=2, padx=4)
                    frSend.grid_columnconfigure(0, weight=1)
                    self.balloon.bind(frSend,
                                      'Screenshot linkage: Press the shortcut key to perform screenshot OCR and copy the result to the clipboard,\nThen send the specified keyboard keys\nCan be used to link tools such as translators or AHK\nTimes: the number of times to repeatedly send keystrokes, such as 2 is double click')
                    wid = Widget.hotkeyFrame(
                        frSend, 'Screenshot linkage shortcut key', 'FinishSend', func=self.openLinkageScreenshot, isAutoBind=True)
                    wid.grid(column=0, row=0, sticky="nsew")
                    wid = Widget.hotkeyFrame(
                        frSend, 'Linked send button', 'FinishSend2', isAutoBind=False, isCheckBtn=False)
                    wid.grid(column=0, row=1, sticky="nsew")
                    tk.Entry(frSend, width=2, textvariable=Config.getTK('hotkeyFinishSendNumber')
                             ).grid(column=1, row=1)
                    tk.Label(frSend, text='times').grid(column=2, row=1)

                # 切换截图模式
                def onModeChange():
                    isHotkey = Config.get('isHotkeyScreenshot')
                    scsName = Config.get('scsModeName')
                    umihk = Config.get('hotkeyScreenshot')
                    scsMode = Config.get('scsMode').get(
                        scsName, ScsModeFlag.multi)  # Current screenshot mode
                    if scsMode == ScsModeFlag.system:  # Switch to system screenshot
                        fhkUmi.forget()
                        fhkSys.pack(side='top', fill='x', padx=4)
                        self.updateFrameHeight()  # Refresh the frame
                        if isHotkey:  # Currently registered
                            if umihk:  # Screenshot of logout software
                                Widget.delHotkey(umihk)  # Logout button
                            Hotkey.add(syssscom,  # Add shortcut key monitoring
                                       lambda *e: self.win.event_generate('<<ScreenshotEvent>>'))
                    elif scsMode == ScsModeFlag.multi:  # Switch to software screenshot
                        fhkSys.forget()
                        fhkUmi.pack(side='top', fill='x', padx=4)
                        self.updateFrameHeight()  # Refresh the frame
                        if isHotkey:
                            Widget.delHotkey(syssscom)  # Logout button
                            if umihk:
                                Hotkey.add(umihk,  # Add shortcut key monitoring
                                           lambda *e: self.win.event_generate('<<ScreenshotEvent>>'))
                    Log.info(f'Screenshot mode change: {scsMode}')

                Config.addTrace('scsModeName', onModeChange)
                onModeChange()

            quickOCR()

            # 批量任务设置
            frameBatch = tk.LabelFrame(self.optFrame, text="batchTasks")
            frameBatch.pack(side='top', fill='x',
                            ipady=2, pady=LabelFramePadY, padx=4)

            def initScheduler():  # Scheduled task settings
                frameScheduler = tk.LabelFrame(
                    frameBatch, labelanchor='n', text="Scheduled task")
                frameScheduler.pack(side='top', fill='x',
                                    ipady=2, pady=LabelFramePadY, padx=4)

                fr1 = tk.Frame(frameScheduler)
                fr1.pack(side='top', fill='x', pady=2, padx=5)
                ttk.Checkbutton(fr1, text="Open file after completion",
                                variable=Config.getTK('isOpenOutputFile')).pack(side='left')
                ttk.Checkbutton(fr1, text="Open directory after completion",
                                variable=Config.getTK('isOpenExplorer'), ).pack(side='left', padx=15)

                fr2 = tk.Frame(frameScheduler)
                fr2.pack(side='top', fill='x', pady=2, padx=5)
                ttk.Checkbutton(fr2, text='Execute after this completion',
                                variable=Config.getTK('isOkMission')).pack(side='left')
                okMissionDict = Config.get("okMission")
                okMissionNameList = [i for i in okMissionDict.keys()]
                wid = ttk.Combobox(fr2, width=14, state="readonly", textvariable=Config.getTK('okMissionName'),
                                   value=okMissionNameList)
                wid.pack(side='left')
                self.balloon.bind(wid,
                                  'You can open the software configuration json file and add your own tasks (cmd command)')
                if Config.get("okMissionName") not in okMissionNameList:
                    wid.current(0)  # Initialize Combobox and okMissionName

            initScheduler()

            def initInFile():  # Input settings
                fInput = tk.LabelFrame(
                    frameBatch, labelanchor='n', text='Image import')
                fInput.pack(side='top', fill='x',
                            ipady=2, pady=LabelFramePadY, padx=4)
                self.balloon.bind(
                    fInput, f"Allowed image formats:\n{Config.get('imageSuffix')}")

                fr1 = tk.Frame(fInput)
                fr1.pack(side='top', fill='x', pady=2, padx=5)
                wid = ttk.Checkbutton(
                    fr1, variable=Config.getTK('isRecursiveSearch'), text='Recursively read all pictures in subfolders')
                wid.grid(column=0, row=0, columnspan=2, sticky='w')
                self.lockWidget.append(wid)
                if Config.get('isAdvanced'):  # Hide advanced options: modify image license suffix
                    tk.Label(fr1, text='Picture suffix: ').grid(
                        column=0, row=2, sticky='w')
                    enInSuffix = tk.Entry(
                        fr1, textvariable=Config.getTK('imageSuffix'))
                    enInSuffix.grid(column=1, row=2, sticky='nsew')
                    self.lockWidget.append(enInSuffix)

                fr1.grid_columnconfigure(1, weight=1)

            initInFile()

            def initOutFile():  # Output settings
                fOutput = tk.LabelFrame(
                    frameBatch, labelanchor='n', text="result output")
                fOutput.pack(side='top', fill='x',
                             ipady=2, pady=LabelFramePadY, padx=4)
                # Output file type check
                fr1 = tk.Frame(fOutput)
                fr1.pack(side='top', fill='x', pady=2, padx=5)

                wid = ttk.Checkbutton(
                    fr1, variable=Config.getTK('isOutputTxt'), text='Merge .txt files')
                self.balloon.bind(wid, f'Output all recognized text to the same txt file')
                wid.grid(column=0, row=0, sticky='w')
                self.lockWidget.append(wid)
                wid = ttk.Checkbutton(
                    fr1, variable=Config.getTK('isOutputSeparateTxt'), text='independent.txt file')
                self.balloon.bind(wid, f'The text of each picture is output to a separate txt file with the same name')
                wid.grid(column=2, row=0, sticky='w')
                self.lockWidget.append(wid)
                wid = ttk.Checkbutton(
                    fr1, variable=Config.getTK('isOutputMD'), text='Graphic link.md file')
                self.balloon.bind(wid, f'Open with Markdown reader, which can display images and text at the same time')
                wid.grid(column=0, row=1, sticky='w')
                self.lockWidget.append(wid)
                wid = ttk.Checkbutton(
                    fr1, variable=Config.getTK('isOutputJsonl'), text='original information.jsonl file')
                self.balloon.bind(wid,
                                  f'contains all file paths and OCR information, which can be imported into other programs for further operation')
                wid.grid(column=2, row=1, sticky='w')
                self.lockWidget.append(wid)
                tk.Label(fr1, text=' ').grid(column=1, row=0)

                def offAllOutput(e):  # turnOffAllOutput
                   if OCRe.msnFlag == MsnFlag.none:
                        Config.set('isOutputTxt', False)
                        Config.set('isOutputSeparateTxt', False)
                        Config.set('isOutputMD', False)
                        Config.set('isOutputJsonl', False)

                labelOff = tk.Label(fr1, text='Turn off all output',
                                    cursor='hand2', fg='blue')
                labelOff.grid(column=0, row=2, sticky='w')
                labelOff.bind('<Button-1>', offAllOutput) # Bind to turn off all output

                wid = ttk.Checkbutton(fr1, text='When the picture does not contain text, no information will be output',
                                      variable=Config.getTK('isIgnoreNoText'), )
                wid.grid(column=0, row=10, columnspan=9, sticky='w')
                self.lockWidget.append(wid)

                tk.Label(fOutput, fg='gray',
                         text="When the following two items are empty, the default output will be to the folder where the first picture is located."
                         ).pack(side='top', fill='x', padx=5)
                #Output directory
                fr2 = tk.Frame(fOutput)
                fr2.pack(side='top', fill='x', pady=2, padx=5)
                tk.Label(fr2, text="Output directory:").grid(column=0, row=3, sticky='w')
                enOutPath = tk.Entry(
                    fr2, textvariable=Config.getTK('outputFilePath'))
                enOutPath.grid(column=1, row=3, sticky='ew')
                self.lockWidget.append(enOutPath)
                fr2.grid_rowconfigure(4, minsize=2)  # Increase the spacing in the second row
                tk.Label(fr2, text="Output file name:").grid(column=0, row=5, sticky='w')
                enOutName = tk.Entry(
                    fr2, textvariable=Config.getTK('outputFileName'))
                enOutName.grid(column=1, row=5, sticky='ew')
                self.lockWidget.append(enOutName)
                fr2.grid_columnconfigure(1, weight=1)  # The second column is automatically expanded

            initOutFile()

            # 后处理设置
            def initProcess():  # Post-processing settings
                fProcess = tk.LabelFrame(self.optFrame, text='Text post-processing')
                fProcess.pack(side='top', fill='x',
                              ipady=2, pady=LabelFramePadY, padx=4)

                fIgnore = tk.Frame(fProcess)
                fIgnore.pack(side='top', fill='x', pady=2, padx=4)

                self.ignoreBtn = ttk.Button(fIgnore, text='Open the ignore area editor (set exclusion watermark)',
                                            command=self.openSelectArea)
                self.ignoreBtn.pack(side='top', fill='x')
                self.balloon.bind(
                    self.ignoreBtn,
                    'Ignore the specified area in the image\nCan be used to exclude image watermarks during batch recognition')
                self.lockWidget.append(self.ignoreBtn)
                # Ignore the regional ontology frame
                self.ignoreFrame = tk.Frame(fIgnore)  # Do not pack, add dynamically
                self.ignoreFrame.grid_columnconfigure(0, minsize=4)
                wid = ttk.Button(self.ignoreFrame, text='Add area',
                                 command=self.openSelectArea)
                wid.grid(column=1, row=0, sticky='w')
                self.lockWidget.append(wid)
                wid = ttk.Button(self.ignoreFrame, text='Clear area',
                                 command=self.clearArea)
                wid.grid(column=1, row=1, sticky='w')
                self.lockWidget.append(wid)
                self.ignoreLabel = tk.Label(
                    self.ignoreFrame, anchor='w', justify='left')  # Display the effective size
                self.ignoreLabel.grid(column=1, row=2, sticky='n')
                self.balloon.bind(
                    self.ignoreLabel,
                    'In batch tasks, only pictures with the same resolution will have the ignored area applied. ')
                self.ignoreFrame.grid_rowconfigure(2, minsize=10)
                self.ignoreFrame.grid_columnconfigure(2, minsize=4)
                self.canvasHeight = 120  # The height of the drawing board remains unchanged, and the width is adjusted according to the data returned by the selection.
                self.canvas = tk.Canvas(self.ignoreFrame, width=200, height=self.canvasHeight,
                                        bg="black", cursor='hand2')
                self.canvas.grid(column=3, row=0, rowspan=10)
                self.canvas.bind(
                    '<Button-1>', lambda *e: self.openSelectArea())
                fpro = tk.Frame(fProcess)
                fpro.pack(side='top', fill='x', pady=2, padx=4)
                fpro.grid_columnconfigure(0, weight=1)
                wid = Widget.comboboxFrame(
                    fpro, 'Merge paragraphs: ', 'tbpu', self.lockWidget)
                wid.grid(column=0, row=0, sticky='ew')
                self.balloon.bind(wid,
                                  'Merge the single lines of text divided by OCR into the entire text\nClick the button on the right to browse the solution description')
                labelUse = tk.Label(fpro, text='Description', width=5,
                                    fg='deeppink', cursor='question_arrow')
                labelUse.grid(column=1, row=0)
                labelUse.bind(
                    '<Button-1>', lambda *e: self.showTips(GetTbpuHelp(Umi.website)))  # Bind left mouse button click

            initProcess()

            def initOcrUI():  # OCR engine settings
                frameOCR = tk.LabelFrame(
                    self.optFrame, text="OCR recognition engine settings")
                frameOCR.pack(side='top', fill='x', ipady=2,
                              pady=LabelFramePadY, padx=4)
                wid = Widget.comboboxFrame(
                    frameOCR, 'Recognition language: ', 'ocrConfig', self.lockWidget)
                wid.pack(side='top', fill='x', pady=2, padx=5)
                self.balloon.bind(
                    wid,
                    'This software has organized multi-language expansion packages, which can import more language model libraries.\nYou can also manually import PaddleOCR-compatible model libraries.\nFor details, please visit the project Github homepage\n\nVertical model library (recognition Language) It is recommended to use it with vertical merged paragraphs')
                # Compression
                fLim = tk.Frame(frameOCR)
                fLim.pack(side='top', fill='x', pady=2, padx=5)
                self.balloon.bind(
                    fLim,
                    'Long edge compression mode can greatly speed up the recognition speed, but may reduce the recognition accuracy of large-resolution images\nFor images larger than 4000 pixels, the value can be changed to half of the maximum edge length. Must be an integer greater than zero\nDefault value: 960\n\nShort edge enlargement mode may improve the accuracy of small resolution images. Generally not needed')
                Widget.comboboxFrame(
                    fLim, 'Scale preprocessing:', 'ocrLimitMode', self.lockWidget, 14).pack(side='left')
                tk.Label(fLim, text='to').pack(side='left')
                wid = tk.Entry(
                    fLim, width=9, textvariable=Config.getTK('ocrLimitSize'))
                wid.pack(side='left')
                self.lockWidget.append(wid)
                tk.Label(fLim, text='pixel').pack(side='left')
                # direction
                wid = ttk.Checkbutton(frameOCR, text='Enable direction classifier (text deflection 90 degrees/180 degrees direction correction)',
                                      variable=Config.getTK('isOcrAngle'))
                wid.pack(side='top', fill='x', pady=2, padx=5)
                self.balloon.bind(
                    wid, 'When the text in the picture is deflected by 90 degrees or 180 degrees, please turn on this option\nIt may slightly reduce the recognition speed\nThere is no need to enable this option for small angle deflections')
                self.lockWidget.append(wid)
                # CPU
                fCpu = tk.Frame(frameOCR, padx=5)
                fCpu.pack(side='top', fill='x')
                tk.Label(fCpu, text='Number of threads:').pack(side='left')
                wid = tk.Entry(
                    fCpu, width=6, textvariable=Config.getTK('ocrCpuThreads'))
                wid.pack(side='left')
                self.lockWidget.append(wid)
                self.balloon.bind(
                    wid, 'is preferably equal to the number of threads in the CPU. Must be an integer greater than zero')
                wid = ttk.Checkbutton(fCpu, text='Enable MKLDNN acceleration',
                                      variable=Config.getTK('isOcrMkldnn'))
                wid.pack(side='left', padx=40)
                self.balloon.bind(
                    wid, 'Significantly speed up recognition. Memory usage will also increase')
                self.lockWidget.append(wid)

                # grid
                fr1 = tk.Frame(frameOCR)
                fr1.pack(side='top', fill='x', padx=5)
                if Config.get('isAdvanced'):
                    #Hide advanced options: additional startup parameters
                    tk.Label(fr1, text='Additional startup parameters:').grid(
                        column=0, row=2, sticky='w')
                    wid = tk.Entry(
                        fr1, textvariable=Config.getTK('argsStr'))
                    wid.grid(column=1, row=2, sticky="nsew")
                    self.balloon.bind(
                        wid, 'OCR advanced parameter command. Please comply with the format required by PaddleOCR-json. Please refer to the project homepage for details')
                    self.lockWidget.append(wid)
                    # Hide advanced options: engine management strategy
                    Widget.comboboxFrame(fr1, 'Engine management strategy:', 'ocrRunMode', self.lockWidget
                                         ).grid(column=0, row=6, columnspan=2, sticky='we')
                    #Hide advanced options: engine startup timeout
                    fInit = tk.Frame(fr1)
                    fInit.grid(column=0, row=7, columnspan=2,
                               sticky='we', pady=2)
                    self.balloon.bind(
                        fInit, 'When the engine starts, if the initialization is not completed after this time limit, it is judged as a startup failure')
                    tk.Label(fInit, text='Initialization timeout determination:').pack(side='left')
                    tk.Entry(fInit, width=5,
                             textvariable=Config.getTK('ocrInitTimeout')).pack(side='left')
                    tk.Label(fInit, text='seconds').pack(side='left')

                    #Hide advanced options: automatically clean memory
                    fRam = tk.Frame(fr1)
                    fRam.grid(column=0, row=8, columnspan=2,
                              sticky='we', pady=2)
                    tk.Label(fRam, text='Automatically clean up memory: takes up more than').pack(side='left')
                    wid = tk.Entry(
                        fRam, width=5, textvariable=Config.getTK('ocrRamMaxFootprint'))
                    wid.pack(side='left')
                    self.lockWidget.append(wid)
                    tk.Label(fRam, text='MB or free').pack(side='left')
                    wid = tk.Entry(
                        fRam, width=5, textvariable=Config.getTK('ocrRamMaxTime'))
                    wid.pack(side='left')
                    self.lockWidget.append(wid)
                    tk.Label(fRam, text='second').pack(side='left')
                    self.balloon.bind(
                        fRam,
                        'It takes effect when the engine policy is "Resident in the background"\nThe occupied memory exceeds the specified value, or there is no task execution within the specified time, the memory will be cleared once\nFrequently cleaning the memory will cause lag and affect the user experience\nIt is recommended not to occupy Less than 1500 MB, idle for not less than 10 seconds\nThe two conditions take effect independently. Ignore this condition when filling in 0')

                frState = tk.Frame(fr1)
                frState.grid(column=0, row=10, columnspan=2, sticky='nsew')
                tk.Label(frState, text='Current status of engine:').pack(
                    side='left')
                tk.Label(frState, textvariable=Config.getTK('ocrProcessStatus')).pack(
                    side='left')
                labStop = tk.Label(frState, text="Stop",
                                   cursor='hand2', fg="red")
                labStop.pack(side='right')
                self.balloon.bind(labStop, 'Force stop the engine process')
                labStart = tk.Label(frState, text="Start",
                                    cursor='hand2', fg='blue')
                labStart.pack(side='right', padx=5)

                def engStart():
                    try:
                        OCRe.start()
                    except Exception as err:
                        tk.messagebox.showerror(
                            'Encountered hundreds of millions of small problems',
                            f'Engine startup failed: {err}')

                labStart.bind(
                    '<Button-1>', lambda *e: engStart())
                labStop.bind(
                    '<Button-1>', lambda *e: OCRe.stop())

                fr1.grid_rowconfigure(1, minsize=4)
                fr1.grid_rowconfigure(3, minsize=4)
                fr1.grid_columnconfigure(1, weight=1)

            initOcrUI()

            def initAbout():  # 关于面板
                frameAbout = tk.LabelFrame(
                    self.optFrame, text='About')
                frameAbout.pack(side='top', fill='x', ipady=2,
                                pady=LabelFramePadY, padx=4)
                tk.Label(frameAbout, image=Asset.getImgTK(
                    'umiocr64')).pack() # icon
                tk.Label(frameAbout, text=Umi.name, fg='gray').pack()
                tk.Label(frameAbout, text=Umi.about, fg='gray').pack()
                labelWeb = tk.Label(frameAbout, text=Umi.website, cursor='hand2',
                                    fg='deeppink')
                labelWeb.pack() # text
                labelWeb.bind( # Bind the left mouse button to click and open the web page
                    '<Button-1>', lambda *e: webOpen(Umi.website))

            initAbout()

            def initEX():  # 额外
                fEX = tk.Frame(self.optFrame)
                fEX.pack(side='top', fill='x', padx=4)
                labelOpenFile = tk.Label(
                    fEX, text='Open settings file', fg='gray', cursor='hand2')
                labelOpenFile.pack(side='left')
                labelOpenFile.bind(
                    '<Button-1>', lambda *e: os.startfile('Umi-OCR_config.json'))
                self.balloon.bind(labelOpenFile, 'Umi-OCR_config.json')
                wid = tk.Checkbutton(fEX, text='Debug Mode', fg='gray',
                                     variable=Config.getTK('isDebug'))
                self.balloon.bind(
                    wid, 'Debugging function, for developers to use, effective immediately:\nOCR outputs additional debugging information | Built-in screenshot display debugger')
                wid.pack(side='right')
                # Hide advanced options
                wid = tk.Checkbutton(fEX, text='Advanced Options', fg='gray',
                                     variable=Config.getTK('isAdvanced'))
                self.balloon.bind(
                    wid, 'Enable hidden advanced options, effective after restart')
                wid.pack(side='right', padx=10)
                # If it is not pinned to the top initially and no prompt is displayed, space will be reserved at the end.
                if not Config.get('isWindowTop'):
                    tk.Label(self.optFrame).pack(side='top')

            initEX()

            def initOptFrameWH():  #Initialize the width and height of the frame
                self.updateFrameHeight()
                self.optCanvasWidth = 1 #The width changes with the window size.

                def onCanvasResize(event): # Bind the canvas size change event
                    cW = event.width - 3 # Current canvas width
                    if not cW == self.optCanvasWidth: # If different from last time:
                        self.optFrame['width'] = cW # Modify the frame width of the settings page
                        self.optCanvasWidth = cW

                self.optCanvas.bind( # Bind the canvas size change event. It will only be triggered when the canvas component is displayed in the foreground, reducing performance usage
                    '<Configure>', onCanvasResize)

                def onCanvasMouseWheel(event): # Bind the scroll wheel event in the canvas
                    self.optCanvas.yview_scroll(
                        1 if event.delta < 0 else -1, "units")

                self.optCanvas.bind_all('<MouseWheel>', onCanvasMouseWheel)
                # Unbind the default scroll wheel event for all check boxes to prevent accidental touches
                self.win.unbind_class('TCombobox', '<MouseWheel>')

            initOptFrameWH()

        initTab3()

        # parseStartupParameters
        flags = Parse(argv)
        if 'error' in flags:
            tk.messagebox.showerror(
                '遇到了一点小问题', flags['error'])
        # Start tray
        if Config.get('isTray'):
            SysTray.start()
            self.win.wm_protocol( # Register window closing event
                'WM_DELETE_WINDOW', self.onCloseWin)
            # ↑ Therefore, when the tray is not started, the × of the window is not associated with any event and is the default exit software.
            if not flags['hide']: # Non-silent mode
                self.gotoTop() #Restore the main window display
        else: # No tray, force display of main window
            self.gotoTop()
        self.win.after(1, Config.initOK) # Mark initialization completed
        if flags['img'] or flags['clipboard'] or flags['screenshot']: # There is an initial task
            self.win.after(10, Mission(flags))
        Notify('Welcome to Umi-OCR', 'Notification pop-up window has been opened')
        self.win.mainloop()

    # 加载图片 ===============================================

    def draggedImages(self, paths):  # Drag in pictures
        if not self.isMsnReady():
            tk.messagebox.showwarning(
                'Task in progress', 'Please stop the task before dragging in the picture')
            return
        self.notebook.select(self.notebookTab[0]) # Switch to the table tab
        pathList = []
        for p in paths: # byte to string
            pathList.append(p.decode(Config.sysEncoding, # Decode according to system encoding
                                     errors='ignore'))
        self.addImagesList(pathList)

    def openFileWin(self): # Open the file selection window
        if not self.isMsnReady():
            return
        suf = Config.get('imageSuffix') # License suffix
        paths = tk.filedialog.askopenfilenames(
            title='Select picture', filetypes=[('Picture', suf)])
        self.addImagesList(paths)

    def addImagesList(self, paths):  # Add a list of images
        if not self.isMsnReady():
            tk.messagebox.showwarning(
                'Task in progress', 'Please stop the task before adding an image')
            return
        suf = Config.get('imageSuffix').split()  # List of permission suffixes

        def addImage(path):  # Add an image. Incoming path, permission suffix.
            path = path.replace("/", "\\")  # Browse is a left slash, drag in is a right slash; Unification is needed
            if suf and os.path.splitext(path)[1].lower() not in suf:
                return  # needs to identify the license suffix and the file suffix is not in the license and is not added.
            # Detect duplicates
            if self.batList.isDataItem('path', path):
                return
            # Detect availability
            try:
                s = Image.open(path).size
            except Exception as e:
                tk.messagebox.showwarning(
                    "A minor problem was encountered",
                    f" image failed to load. Image address:\n{path}\n\nError message:\n{e}")
                return
            # Calculate the path
            p = os.path.abspath(os.path.join(path, os.pardir))  # parent folder
            if not Config.get("outputFilePath"):  # Initialize the output path
                Config.set("outputFilePath", p)
            if not Config.get("outputFileName"):  # Initialize the output file name
                n = f"[transtext]_{os.path.basename(p)}"
                Config.set("outputFileName", n)
            # Add to Pending List
            name = os.path.basename(path)  # The suffix filename
            tableInfo = (name, "", "")
            id = self.table.insert('', 'end', values=tableInfo)  # Add to the table component
            dictInfo = {"name": name, "path": path, "size": s}
            self.batList.append(id, dictInfo)

        isRecursiveSearch = Config.get("isRecursiveSearch")
        for path in paths: # Traverse all dragged paths
            if os.path.isdir(path): # If it is a directory
                if isRecursiveSearch: # Requires recursive subfolders
                    for subDir, dirs, subFiles in os.walk(path):
                        for s in subFiles:
                            addImage(subDir + "\\" + s)
                else: # Non-recursive, only search one level of subfolders
                    subFiles = os.listdir(path) # Traverse subfiles
                    for s in subFiles:
                        addImage(path + "\\" + s) # Add
            elif os.path.isfile(path): # If it is a file:
                addImage(path) # Add directly

    # ignoreArea ===============================================

    def openSelectArea(self):  # openSelectionArea
        if not self.isMsnReady() or not self.win.attributes('-disabled') == 0:
            return
        defaultPath = ""
        if not self.batList.isEmpty():
            defaultPath = self.batList.get(index=0)["path"]
        self.win.attributes("-disabled", 1)  # disableParentWindow
        IgnoreAreaWin(self.closeSelectArea, defaultPath)

    def closeSelectArea(self):  #Close the selection area and obtain the selection area data
        self.win.attributes("-disabled", 0) # Enable parent window
        area = Config.get("ignoreArea")
        if not area:
            self.ignoreFrame.pack_forget() #Hide the ignore area window
            self.ignoreBtn.pack(side='top', fill='x') #Show button
            self.updateFrameHeight() # Refresh the frame
            return
        self.ignoreLabel["text"] = f"Effective resolution:\nWidth {area['size'][0]}\nHeight {area['size'][1]}"
        self.canvas.delete(tk.ALL) # Clear canvas
        scale = self.canvasHeight / area['size'][1] #Display scaling ratio
        width = round(self.canvasHeight * (area['size'][0] / area['size'][1]))
        self.canvas['width'] = width
        areaColor = ["red", "green", "darkorange"]
        tran = 2 # draw offset
        for i in range(3): # Draw a new graph
            for a in area['area'][i]:
                x0, y0 = a[0][0] * scale + tran, a[0][1] * scale + tran,
                x1, y1 = a[1][0] * scale + tran, a[1][1] * scale + tran,
                self.canvas.create_rectangle(
                    x0, y0, x1, y1, fill=areaColor[i])
        self.ignoreBtn.pack_forget() # Hide button
        self.ignoreFrame.pack(side='top', fill='x') # Display the ignore area window
        self.updateFrameHeight() # Refresh the frame

    def clearArea(self):  # 清空忽略区域
        self.ignoreFrame.pack_forget()  # 隐藏忽略区域窗口
        self.ignoreBtn.pack(side='top', fill='x')  # 显示按钮
        self.updateFrameHeight()  # 刷新框架
        Config.set("ignoreArea", None)
        self.canvas.delete(tk.ALL)  # 清除画布
        self.canvas['width'] = int(self.canvasHeight * (16 / 9))

    # 表格操作 ===============================================

    def clearTable(self):  # 清空表格
        if not self.isMsnReady():
            return
        self.progressbar["value"] = 0
        Config.set('tipsTop1', '')
        Config.set('tipsTop2', '请导入文件')
        Config.set("outputFilePath", "")
        Config.set("outputFileName", "")
        self.batList.clear()
        chi = self.table.get_children()
        for i in chi:
            self.table.delete(i)  # 表格组件移除

    def delImgList(self):  # 图片列表中删除选中
        if not self.isMsnReady():
            return
        chi = self.table.selection()
        for i in chi:
            self.table.delete(i)
            self.batList.delete(key=i)

    def setTableItem(self, time, score, key=None, index=-1):  # 改变表中第index项的数据信息
        if not key:
            key = self.batList.indexToKey(index)
        self.table.set(key, column='time', value=time)
        self.table.set(key, column='score', value=score)

    def clearTableItem(self):  # 清空表格数据信息
        keys = self.batList.getKeys()
        for key in keys:  # 清空表格参数
            self.table.set(key, column='time', value="")
            self.table.set(key, column='score', value="")

    # 写字板操作 =============================================

    def panelOutput(self, text, position=tk.END, highlight=''):
        '''输出面板写入文字'''
        self.textOutput.insert(position, text)
        if highlight:  # 需要高亮
            if position == tk.END:  # 暂时只允许尾部插入
                self.textOutput.tag_add(  # 尾部插入要高亮前一行
                    highlight, f'end -1lines linestart', f'end -1lines lineend')
        if self.isAutoRoll.get():  # 需要自动滚动
            self.textOutput.see(position)

    def errorOutput(self, title, msg='', highlight='red'):
        '''Output error message'''
        Notify(title, msg)
        if not self.textOutput.get('end-2c') == '\n': # If there is no line break at the end of the current panel, add a line break
            self.panelOutput('\n')
        self.panelOutput(title, highlight=highlight) # Output red prompt
        if msg:
            self.panelOutput('\n' + msg)
        self.panelOutput('\n')

    def panelClear(self):
        '''Clear the output panel'''
        self.textOutput.delete('1.0', tk.END)

    # 窗口操作 =============================================

    def updateFrameHeight(self):  # refreshSettingsPageFrameHeight
        self.optFrame.pack_propagate(True) # Enable automatic frame width and height adjustment
        self.optFrame.update() # Force refresh
        rH = self.optFrame.winfo_height() # The height of the frame supported by the component
        self.optCanvas.config(scrollregion=(0, 0, 0, rH)) # The height of the canvas is the height of the frame
        self.optFrame.pack_propagate(False) # Disable automatic frame width and height adjustment
        self.optFrame["height"] = rH # Manually restore height

    def gotoTop(self, isForce=False):  # mainWindowOnTop
        flag = Config.get('WindowTopMode')
        # Mode: silent mode
        if flag == WindowTopModeFlag.never and not isForce and Config.get('isTray'):
            self.win.attributes('-topmost', 0)
            return
        # Mode: pop up automatically, or does not meet the requirements of silent mode
        if self.win.state() == 'iconic': # When the window is minimized
            self.win.state('normal') #Restore the foreground state
        self.win.attributes('-topmost', 1) # Set the top level
        geometry = self.win.geometry() # Cache the current position and size of the main window
        self.win.deiconify() #The main window gets focus
        self.win.geometry(geometry) # If the main window is welting, getting focus will exit welt mode, so reset the position to restore welting.
        # If the window is not set to the top, the top level will be canceled after a period of time.
        if not Config.get('isWindowTop'):
            self.win.after(500, lambda: self.win.attributes('-topmost', 0))

    # 进行任务 ===============================================

    def isMsnReady(self):
        '''可以操作下一次任务时返回T'''
        return OCRe.msnFlag == MsnFlag.none

    def setRunning(self, batFlag):  # 设置运行状态。

        def setNone():
            self.btnRun['text'] = 'Start task'
            self.btnRun['state'] = 'normal'
            Config.set('tipsTop2', 'Ended')
            return 'normal'

        def initing():
            self.btnRun['text'] = 'Stop task'
            self.btnRun['state'] = 'normal'
            Config.set('tipsTop1', '')
            Config.set('tipsTop2', 'Initialization')
            self.progressbar["maximum"] = 50 #Reset the length of the progress bar. The smaller the value, the faster the animation will be loaded.
            self.progressbar['mode'] = 'indeterminate' # The progress bar is in scroll mode
            self.progressbar.start() # The progress bar starts loading animation
            return 'disable'

        def running():
            self.progressbar.stop() # The progress bar stops loading animation
            self.progressbar['mode'] = 'determinate' # Progress bar static mode
            return ''

        def stopping():
            self.btnRun['text'] = 'Stopping'
            self.btnRun['state'] = 'disable'
            if str(self.progressbar["mode"]) == 'indeterminate':
                self.progressbar.stop() # The progress bar stops loading animation
                self.progressbar['mode'] = 'determinate' # Progress bar static mode
            return ''

        state = {
            MsnFlag.none: setNone,
            MsnFlag.initing: initing,
            MsnFlag.running: running,
            MsnFlag.stopping: stopping,
        }.get(batFlag, '')()
        if state:
            for w in self.lockWidget: # Change component state (disabled, enabled)
                if 'widget' in w.keys() and 'stateOFnormal' in w.keys():
                    if state == 'normal':
                        w['widget']['state'] = w['stateOFnormal'] # The normal state is a special value
                    else:
                        w['widget']['state'] = state
                elif 'state' in w.keys():
                    w['state'] = state
        self.win.update()

    def run(self):  # RUN BUTTON TRIGGER
        if self.isMsnReady(): # Not running
            if self.batList.isEmpty():
                return
            # Initialize batch image recognition task processor
            try:
                msnBat = MsnBatch()
            except Exception as err:
                tk.messagebox.showwarning('Encountered hundreds of millions of minor problems', f'{err}')
                return # The run has not started yet, terminate this run.
            # start operation
            paths = self.batList.getItemValueList('path')
            OCRe.runMission(paths, msnBat)
        # Allow tasks to be stopped in progress or during initialization
        elif OCRe.msnFlag == MsnFlag.running or OCRe.msnFlag == MsnFlag.initiating:
            OCRe.stopByMode()

    def startSingleClipboard(self):  # Start the clipboard task of single image recognition
        try: # Initialize the quick image recognition task processor
            msnQui = MsnQuick()
        except Exception as err:
            tk.messagebox.showwarning('Encountered hundreds of millions of minor problems', f'{err}')
            return # The run has not started yet, terminate this run.
        # start operation
        OCRe.runMission(['clipboard'], msnQui)
        self.notebook.select(self.notebookTab[1]) # Go to the output card
        self.gotoTop() # Keep the main window on top

    def runClipboard(self, e=None): # Identify clipboard
        if not self.isMsnReady(): # Running, not executing
            return
        clipData = Tool.getClipboardFormat() # Read the clipboard

        failFlag = False

        # The clipboard is a bitmap (first)
        if isinstance(clipData, int):
            self.startSingleClipboard()

        # There is a list of files in the clipboard (ctrl+c on the file in the file manager to get the handle)
        elif isinstance(clipData, tuple):
            # Check whether there is a legal file type in the file list
            suf = Config.get('imageSuffix').split() # Allowed suffix list
            flag=False
            for path in clipData: # Check whether the license suffix exists in the file list
                if suf and os.path.splitext(path)[1].lower() in suf:
                    flag = True
                    break
            # If it exists, load the file into the main table and execute the task
            if flag:
                self.notebook.select(self.notebookTab[0]) # Go to the main table card
                self.gotoTop() # Keep the main window on top
                self.clearTable() # Clear the main table
                self.addImagesList(clipData) #Add to main table
                self.run() # Start task task
            else:
                failFlag = True
        else: # The format in the clipboard is not supported
            failFlag = True

        if failFlag:
            self.errorOutput('No picture information found in the clipboard')
            #Put it on top even if it fails
            self.gotoTop() # Keep the main window on top
            self.notebook.select(self.notebookTab[1]) # Go to the output card

    def runScreenshot(self):  # 进行截图
        if not self.isMsnReady() or not self.win.attributes('-disabled') == 0:
            return
        self.win.attributes("-disabled", 1)  # 禁用主窗口
        if Config.get('isScreenshotHideWindow'):  # 截图时隐藏主窗口
            self.win.state('iconic')
            self.win.after(Config.get('screenshotHideWindowWaitTime'),
                           ScreenshotCopy)  # 延迟，等待最小化完成再截屏
        else:
            ScreenshotCopy()  # 立即截屏

    def openScreenshot(self, e=None):  # 普通截图
        Config.set('isFinishSend', False)
        self.runScreenshot()

    def openLinkageScreenshot(self, e=None):  # 联动截图
        Config.set('isFinishSend', True)
        self.runScreenshot()

    def closeScreenshot(self, flag, errMsg=None):  # Close the screenshot window and return T to indicate that it has been copied to the clipboard
        self.win.attributes("-disabled", 0) # Enable parent window
        if errMsg:
            self.errorOutput('Screenshot failed', errMsg)
        if not flag and self.win.state() == 'normal': # The screenshot is unsuccessful, but the window is not minimized
            self.gotoTop() # Keep the main window on top
        elif flag: # success
            # self.win.after(50, self.runClipboard)
            self.startSingleClipboard() # Clipboard recognition

    def onCloseWin(self):  # closeWindowEvent
        if Config.get('isBackground'):
            self.win.withdraw() # Hide window
        else:
            self.onClose() # Close directly

    def onClose(self):  # closeSoftware
        OCRe.stop() # Forcefully close the engine process and speed up the end of the child thread
        if OCRe.engFlag == EngFlag.none and OCRe.msnFlag == MsnFlag.none: # Not running
            self.exit()
        else:
            self.win.after(50, self.waitClose) # Wait for closure, poll once every 50ms to see if the child thread has ended

    def waitClose(self):  # 等待线程关闭后销毁窗口
        Log.info(f'Close, waiting for {OCRe.engFlag} | {OCRe.msnFlag}')
        if OCRe.engFlag == EngFlag.none and OCRe.msnFlag == MsnFlag.none: # Not running
            self.exit()
        else:
            self.win.after(50, self.waitClose) # Wait for closure, poll once every 50ms to see if the child process has ended

    def exit(self):
        SysTray.stop()  # Close the tray. There is judgment in this function and it will not cause infinite recursion.
        # Wait for a period of time to ensure that the tray thread is closed and the icon is logged out from the system.
        # Then forcefully terminate the main process to prevent the engine sub-threads from surviving
        self.win.after(100, lambda: os._exit(0))

    def showTips(self, tipsText):  # Show tips
        if not self.isMsnReady():
            tk.messagebox.showwarning(
                'Task in progress', 'Please stop the task and then open the software instructions')
            return
        self.notebook.select(self.notebookTab[1])  # Switch to the output tab
        outputNow = self.textOutput.get("1.0", tk.END)
        if outputNow and not outputNow == "\n":  # The output panel content exists and is not a single line break (initial state)
            if not tkinter.messagebox.askokcancel('Prompt',
                                                  'The output panel will be cleared. Do you want to continue?'):
                return
            self.panelClear()
        self.textOutput.insert(tk.END, tipsText)

# 全角空格：【　】

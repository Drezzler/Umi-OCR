from ocr.engine import OCRe # Engine singleton
from utils.asset import Asset # Resource
from utils.config import Config
from ui.widget import Widget # Control

import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
from windnd import hook_dropfiles # File drag and drop
from PIL import Image, ImageTk
import os


class IgnoreAreaWin:
    def __init__(self, closeSendData=None, defaultPath=""):
        self.closeSendData = closeSendData #Interface for sending data to the parent window
        self.balloon = Config.main.balloon # Bubble box
        self.cW = 960 # Artboard size
        self.cH = 540
        self.tran = 2 # Draw offset
        self.areaColor = ["red", "green", #The logo color of each rectangular area
                          "darkorange", "white"]

        # def initWin(): # Initialize the main window
        # Main window
        self.win = tk.Toplevel()
        self.win.protocol("WM_DELETE_WINDOW", self.onClose)
        self.win.title("SELECT AREA")
        self.win.resizable(False, False) # Disable window stretching
        #Variable initialization
        self.imgSize = (-1, -1) # Image size, effective when first loaded.
        self.imgScale = -1 # Image scaling ratio
        self.imgSizeText = tk.StringVar(value="not set")
        self.area = [[], [], []] # Store a list of each rectangular area
        self.areaHistory = [] # Drawing history, used for undoing
        self.areaTextRec = [] # Text area prompt box
        self.areaType = -1 #Current drawing mode
        self.areaTypeIndex = [-1, -1, -1] # The serial number of the currently drawn rectangle
        self.lastPath = '' #The path of the last imported image
        # icon
        self.win.iconphoto(False, Asset.getImgTK('umiocr24')) # Set the window icon
        # initWin()

        # def initPanel(): # Initialize the panel
        tk.Frame(self.win, height=10).pack(side='top')
        ctrlFrame = tk.Frame(self.win)
        ctrlFrame.pack(side='top', fill='y')
        ctrlF0 = tk.Frame(ctrlFrame)
        ctrlF0.pack(side='left')
        tk.Label(ctrlF0, text="[Image resolution]").pack()
        tk.Label(ctrlF0, textvariable=self.imgSizeText).pack()
        tk.Label(ctrlF0, text="Pictures that do not meet this resolution\nIgnoring regional settings will not take effect",
                 fg='gray', wraplength=120).pack()
        tk.Frame(ctrlFrame, w=22).pack(side='left')
        # checkbox
        ctrlF1 = tk.Frame(ctrlFrame)
        ctrlF1.pack(side='left')
        self.isAutoOCR = tk.BooleanVar()
        self.isAutoOCR.set(True)
        wid = ttk.Checkbutton(
            ctrlF1, variable=self.isAutoOCR, text='Enable OCR result preview')
        wid.grid(column=0, row=0, sticky='w')
        self.balloon.bind(wid, 'Mark the text block recognized by OCR with a dotted box')
        wid = ttk.Checkbutton(
            ctrlF1, variable=Config.getTK('isAreaWinAutoTbpu'), text='Enable block post-processing preview')
        Config.addTrace('isAreaWinAutoTbpu', self.reLoadImage)
        wid.grid(column=0, row=1, sticky='w')
        self.balloon.bind(
            wid, 'Mark the blocks that have been post-processed by the text block with a dotted box\nNote that it is only used to preview the post-processing effect.\nIn the actual task, the ignored area is executed earlier than the post-processing and is not affected by the post-processing')
        Widget.comboboxFrame(ctrlF1, '', 'tbpu', width=18).grid(
            column=0, row=2, sticky='w')
        # Switch brush button
        tk.Frame(ctrlFrame, w=30).pack(side='left')
        ctrlF2 = tk.Frame(ctrlFrame)
        ctrlF2.pack(side='left')
        self.buttons = [None, None, None]
        btnW = 15
        self.buttons[0] = tk.Button(ctrlF2, text='+ignore area A', width=btnW, height=3, fg=self.areaColor[0], bg=self.areaColor[3],
                                    command=lambda: self.changeMode(0))
        self.buttons[0].pack(side='left', padx=5)
        self.balloon.bind(
            self.buttons[0], 'The rectangular dotted text block within [ignore area A] will be ignored\nUnder normal circumstances, all the watermark areas that need to be removed can be drawn in area A')
        tk.Frame(ctrlFrame, w=20).pack(side='left')
        self.buttons[1] = tk.Button(ctrlF2, text='+identification area', width=btnW, height=3, fg=self.areaColor[1], bg=self.areaColor[3],
                                    command=lambda: self.changeMode(1))
        self.buttons[1].pack(side='left', padx=5)
        self.balloon.bind(
            self.buttons[1], 'If [identification area] contains a text block, [ignore area A] will be invalid')
        tk.Frame(ctrlFrame, w=20).pack(side='left')
        self.buttons[2] = tk.Button(ctrlF2, text='+ignore area B', width=btnW, height=3, fg=self.areaColor[2], bg=self.areaColor[3],
                                    command=lambda: self.changeMode(2))
        self.buttons[2].pack(side='left', padx=5)
        self.balloon.bind(
            self.buttons[2], 'When [ignore area A] is invalid, that is, when [identify area] is triggered,\n[ignore area B] takes effect')

        tk.Frame(ctrlFrame, w=20).pack(side='left')
        ctrlF4 = tk.Frame(ctrlFrame)
        ctrlF4.pack(side='left')
        tk.Button(ctrlF4, text='clear', width=12, bg='white',
                  command=self.clearCanvas).pack()
        tk.Button(ctrlF4, text='Undo\nCtrl+Shift+Z', width=12, bg='white',
                  command=self.revokeCanvas).pack(pady=5)
        self.win.bind("<Control-Z>", self.revokeCanvas) # Bind the undo key combination with shift
        tk.Frame(ctrlFrame, w=10).pack(side='left')
        tk.Button(ctrlFrame, text='Complete', width=8, bg='white',
                  command=lambda: self.onClose(False)).pack(side="left", fill="y")
        tipsFrame = tk.Frame(self.win)
        tipsFrame.pack()
        tk.Label(tipsFrame, text="↓ ↓ ↓ Drag any picture into the preview below. Then click the button to switch the brush, and press and hold the left button on the picture to select the area you want.",
                 fg='gray').pack(side='left')
        tk.Label(tipsFrame, text="Multiple boxes can be drawn in the same area.", fg='blue').pack(side='left')
        tk.Label(tipsFrame, text="↓ ↓ ↓", fg='gray').pack(side='left')
        # initPanel()

        # def initCanvas(): # Initialize the drawing board
        self.canvas = tk.Canvas(self.win, width=self.cW, height=self.cH,
                                bg="gray", cursor="plus", borderwidth=0)
        self.canvas.bind("<Button-1>", self.mouseDown) # Mouse click
        self.canvas.bind("<B1-Motion>", self.mouseMove) # Mouse movement
        self.canvas.pack()
        hook_dropfiles(self.win, func=self.draggedFiles) # Drag in registration files
        self.canvasImg = None #The image currently being displayed
        # initCanvas()

        def initOCR(): # Initialize the recognizer
            canvasText = self.canvas.create_text(self.cW/2, self.cH/2, font=('', 15, 'bold'), fill='white', anchor="c",
                                                 text=f'The engine is starting, please wait...')
            try:
                OCRe.start() # Start or refresh the engine
            except Exception as e:
                tk.messagebox.showerror(
                    'Encountered hundreds of millions of small problems',
                    f' recognizer initialization failed: {e}\n\nPlease check if there is any problem with the configuration! ')
                self.win.attributes('-topmost', 1) # Set the top level
                self.win.attributes('-topmost', 0) # Then cancel immediately
                self.isAutoOCR.set(False) # Turn off automatic analysis
                return
            finally:
                try:
                    self.canvas.delete(canvasText) # Delete prompt text
                except:
                    pass
        initOCR()

        if defaultPath: #Open the default image
            self.loadImage(defaultPath)

    def onClose(self, isAsk=True): # Click to close. Ask when isAsk is T.

        def getData(): # Pass the data to the interface and then close the window
            area = [[], [], []]
            for i in range(3):
                for a in self.area[i]:
                    a00, a01, a10, a11 = round(
                        a[0][0]/self.imgScale), round(a[0][1]/self.imgScale), round(a[1][0]/self.imgScale), round(a[1][ 1]/self.imgScale)
                    if a00 > a10: # x swap
                        a00, a10 = a10, a00
                    if a01 > a11: # y swap
                        a01, a11 = a11, a01
                    area[i].append([(a00, a01), (a10, a11)])
            return {"size": self.imgSize, "area": area}

        if self.area[0] or self.area[1] or self.area[2]: # Data exists
            if isAsk: # Need to ask
                if tk.messagebox.askokcancel('Close window', 'Do you want to apply the selection?'): # Need to apply
                    Config.set("ignoreArea", getData())
            else: # No need to ask
                Config.set("ignoreArea", getData())
        if self.closeSendData: # If the communication interface exists, return the data
            self.closeSendData()
        OCRe.stopByMode() # Close the OCR process
        self.win.destroy() # Destroy the window

    def draggedFiles(self, paths): # Drag files
        self.loadImage(paths[0].decode( # Decode according to system encoding
            Config.sysEncoding, errors='ignore'))

    def reLoadImage(self): #Load old image
        if self.lastPath:
            self.loadImage(self.lastPath)

    def loadImage(self, path): #Load new image
        """Load images"""
        try:
            img = Image.open(path)
        except Exception as e:
            tk.messagebox.showwarning(
                "Encountered a small problem", f"The image failed to load. Image address:\n{path}\n\nError message:\n{e}")
            self.win.attributes('-topmost', 1) # Set the top level
            self.win.attributes('-topmost', 0) # Then cancel immediately
            return
        # Check image size
        if self.imgSize == (-1, -1): # Initial setting
            self.imgSize = img.size
            # Calculate the scaling ratio by width and height respectively
            sw, sh = self.cW/img.size[0], self.cH/img.size[1]
            # Test, scale according to width or height, just fill the canvas
            if sw > sh: # press high
                self.imgReSize = (round(img.size[0]*sh), self.cH)
                self.imgScale = sh
            else: # press width
                self.imgReSize = (self.cW, round(img.size[1]*sw))
                self.imgScale = sw
            self.imgSizeText.set(f'{self.imgSize[0]}x{self.imgSize[1]}')
        elif not self.imgSize == img.size: # The size does not match
            tk.messagebox.showwarning("The picture size is wrong!",
                                      f"The current image size is limited to {self.imgSize[0]}x{self.imgSize[1]}, and images of {img.size[0]}x{img.size[1]} are not allowed to be loaded.\n To remove restrictions and change to other resolutions, please click 'Clear' and re-drag the image.")
            self.win.attributes('-topmost', 1) # Set the top level
            self.win.attributes('-topmost', 0) # Then cancel immediately
            return
        self.clearCanvasImage() # Clear the last drawn image

        #OCR recognition
        def runOCR():
            # Before task: display prompt information
            self.win.title(f"Under analysis...") #Change the title
            pathStr = path if len(
                path) <= 50 else path[:50]+"..." # The path is too long and cannot be fully displayed, so intercept it
            canvasText = self.canvas.create_text(self.cW/2, self.cH/2, font=('', 15, 'bold'), fill='white', anchor="c",
                                                 text=f'Picture analysis, please wait...\n\n\n\n{pathStr}')
            self.win.update() # Refresh the window
            # Start recognition, it takes a long time
            data = OCRe.run(path)
            #After task: Refresh prompt information
            self.canvas.delete(canvasText) # Delete prompt text
            if data['code'] == 100: # Content exists
                if Config.get('isAreaWinAutoTbpu'): # Post-processing required
                    tbpuClass = Config.get('tbpu').get(
                        Config.get('tbpuName'), None)
                    if tbpuClass:
                        name = os.path.basename(path) #File name with suffix
                        imgInfo = {'name': name,
                                   'path': path, 'size': img.size}
                        tbpu = tbpuClass()
                        data['data'], s = tbpu.run(data['data'], imgInfo)
                for o in data["data"]: # Draw a rectangular box
                    #Extract the coordinates of the upper left corner and lower right corner
                    p1x = round(o['box'][0][0]*self.imgScale)+self.tran
                    p1y = round(o['box'][0][1]*self.imgScale)+self.tran
                    p2x = round(o['box'][2][0]*self.imgScale)+self.tran
                    p2y = round(o['box'][2][1]*self.imgScale)+self.tran
                    r1 = self.canvas.create_rectangle(
                        p1x, p1y, p2x, p2y, outline='white', width=2) # Draw a solid white line base
                    r2 = self.canvas.create_rectangle(
                        p1x, p1y, p2x, p2y, outline='black', width=2, dash=4) # Draw the black dotted line surface
                    self.canvas.tag_lower(r2) # Move to the bottom
                    self.canvas.tag_lower(r1)
                    self.areaTextRec.append(r1)
                    self.areaTextRec.append(r2)
            elif not data["code"] == 101: # An exception occurred
                self.isAutoOCR.set(False) # Turn off automatic analysis
                tk.messagebox.showwarning(
                    "Encountered a small problem", f"Picture analysis failed. Picture address:\n{path}\n\nError code: {str(data['code'])}\n\nError message:\n{ str(data['data'])}")
                self.win.attributes('-topmost', 1) # Set the top level
                self.win.attributes('-topmost', 0) # Then cancel immediately
        if self.isAutoOCR.get():
            try:
                runOCR()
            except Exception as e:
                tk.messagebox.showerror('Encountered a small problem', f'Preview OCR failed:\n{e}')
                return
        self.win.title(f"Select area {path}") #Change title
        #Cache the image and display it
        img = img.resize(self.imgReSize, Image.ANTIALIAS) # Change the image size
        self.imgFile = ImageTk.PhotoImage(img) # Cache images
        self.canvasImg = self.canvas.create_image(
            0, 0, anchor='nw', image=self.imgFile) # Draw the picture
        self.canvas.tag_lower(self.canvasImg) # Move this element to the bottom to prevent blocking the rectangles
        self.lastPath = path

    def changeMode(self, type_): # Switch drawing mode
        if self.imgSize == (-1, -1):
            return
        self.areaType = type_
        for b in self.buttons:
            b["state"] = tk.NORMAL # Enable all buttons
            b["bg"] = self.areaColor[3]
        self.buttons[type_]["state"] = tk.DISABLED # Disable the button just pressed
        self.buttons[type_]["bg"] = self.areaColor[type_] # Switch background color

    def clearCanvasImage(self): # Clear the text box of the image on the canvas, do not clear the ignored box
        self.lastPath = ''
        if self.canvasImg: # Delete image
            self.canvas.delete(self.canvasImg)
        for t in self.areaTextRec: # Delete text box
            self.canvas.delete(t)
        self.areaTextRec = []

    def clearCanvas(self): # Clear the canvas
        self.lastPath = ''
        self.win.title(f"select area") #Change title
        self.area = [[], [], []]
        self.areaHistory = []
        self.areaTextRec = []
        self.areaType = -1
        self.areaTypeIndex = [-1, -1, -1]
        self.imgSize = (-1, -1)
        self.imgSizeText.set("not set")
        self.canvas.delete(tk.ALL)
        for b in self.buttons:
            b["state"] = tk.NORMAL # Enable all buttons
            b["bg"] = self.areaColor[3]

    def revokeCanvas(self, e=None): # Undo a step
        if len(self.areaHistory) == 0:
            return
        self.canvas.delete(self.areaHistory[-1]["id"]) # Delete the last drawn rectangle in the history
        self.area[self.areaHistory[-1]["type"]].pop() # Delete the last rectangular data of the corresponding type
        self.areaHistory.pop() # Delete history records

    def mouseDown(self, event): # When the mouse is pressed, a new rectangle is generated
        if self.areaType == -1:
            return
        x, y = event.x, event.y
        if x > self.imgReSize[0]: # Prevent out of bounds
            x = self.imgReSize[0]
        elif x < 0:
            x = 0
        if y > self.imgReSize[1]:
            y = self.imgReSize[1]
        elif y < 0:
            y = 0
        c = self.areaColor[self.areaType]
        id = self.canvas.create_rectangle( # Draw a new image
            x+self.tran, y+self.tran, x+self.tran, y+self.tran, width=2, activefill=c, outline=c)
        self.area[self.areaType].append([(x, y), (x, y)]) # Add a rectangle to the corresponding list
        self.areaHistory.append({"id": id, "type": self.areaType}) # Load history

    def mouseMove(self, event): # Mouse drag, refresh the last rectangle
        if self.areaType == -1:
            return
        x, y = event.x, event.y
        if x > self.imgReSize[0]: # Prevent out of bounds
            x = self.imgReSize[0]
        elif x < 0:
            x = 0
        if y > self.imgReSize[1]:
            y = self.imgReSize[1]
        elif y < 0:
            y = 0
        x0, y0 = self.area[self.areaType][-1][0][0], self.area[self.areaType][-1][0][1]
        # Refresh the coordinates of the last graphic in the history
        self.canvas.coords(
            self.areaHistory[-1]["id"], x0+self.tran, y0+self.tran, x+self.tran, y+self.tran)
        self.area[self.areaType][-1][1] = (x, y) # Refresh the lower right corner point
# 截图展示
from utils.config import Config
from utils.asset import Asset  # 资源
from ui.win_notify import Notify
from utils.hotkey import Hotkey

import time
import tkinter as tk
from PIL import Image, ImageTk
from win32clipboard import OpenClipboard, EmptyClipboard, SetClipboardData, CloseClipboard, CF_DIB
from io import BytesIO

MinSize = 140 # Minimum size
MaxSizeMargin = 80 # At maximum size, the gap from the edge of the screen
RatioThreshold = 3 # When the aspect ratio of the image is greater than this threshold, the zoom operation only reads the vertical/lateral movement of the mouse to avoid scaling the short side too fast.


class ShowImage:
    def __init__(self, imgPIL=None, imgData=None, title='', initPos=None):
        # imgPIL: PIL object, imgData: bitmap data. Either or both must be passed in.
        # title: window title (optional)
        # initPos: Window initial position (optional), 4-digit list: [upper left x, upper left y, width w, height h]

        #Initialize image data
        self.imgPIL, self.imgData = imgPIL, imgData
        if not self.imgData and not self.imgPIL:
            return
        if not self.imgData: # Create bitmap data from PIL Image object
            output = BytesIO()
            imgPIL.save(output, 'BMP') # Save as bitmap
            self.imgData = output.getvalue()[14:] # Remove header
            output.close()
        if not self.imgPIL: # Create a PIL Image object from bitmap data
            self.imgPIL = Image.open(BytesIO(imgData))
        self.imgTK = ImageTk.PhotoImage(self.imgPIL) # Save the image object
        self.ratio = self.imgPIL.width / self.imgPIL.height # Image ratio
        self.wh = (self.imgPIL.width, self.imgPIL.height) # Current picture width and height

        #Create Tkinter window
        self.win = tk.Toplevel()
        self.win.iconphoto(False, Asset.getImgTK('umiocr24')) # Set the window icon
        self.win.resizable(False, False) # Disable native zoom window
        if not title: # Create title
            title = f'Preview {time.strftime("%H:%M")} ({self.wh[0]}x{self.wh[1]})'
        self.win.title(title)

        # Menu Bar
        self.menubar = tk.Menu(self.win)
        self.win.config(menu=self.menubar)
        self.menubar.add_command(label='lock', command=self.__switchLock)
        self.menubar.add_command(label='identification', command=self.__ocr)
        self.menubar.add_command(label='save', command=self.__saveImage)
        # self.menubar.add_command(label='copy', command=self.copyImage)
        submenu = tk.Menu(self.menubar, tearoff=False)
        submenu.add_command(label='Lock window: Ctrl+T or Ctrl+L',
                            command=lambda *e: self.__switchLock(1))
        submenu.add_command(label='Text recognition: Enter', command=self.__ocr)
        submenu.add_command(label='Save image to local: Ctrl+S', command=self.__saveImage)
        submenu.add_command(label='Copy image to clipboard: Ctrl+C', command=self.__copyImage)
        submenu.add_command(label='Close window: Esc', command=self.__onClose)
        submenu.add_command(label='Move window: drag anywhere')
        submenu.add_command(label='Zoom window: drag the arrow icon in the lower right corner')
        submenu.add_command(label='Zoom window: mouse wheel')
        submenu.add_command(label='Adjust transparency: Ctrl+Scroll wheel')
        self.menubar.add_cascade(label='more', menu=submenu)

        #Create a Canvas object and fill it to fill the entire window
        self.canvas = tk.Canvas(
            self.win, width=self.imgPIL.width, height=self.imgPIL.height, relief='solid')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.config(borderwidth=0, highlightthickness=0) #Hide the Canvas border
        #Create image on Canvas
        self.imgCanvas = self.canvas.create_image(
            0, 0, anchor='nw', image=self.imgTK)

        # Zoom and move related parameters
        imgArr = Asset.getImgTK('zoomArrowAlpha48')
        self.zoomSize = (imgArr.width(), imgArr.height())
        self.mouseOriginXY = None # Starting mouse position for this operation
        self.zoomOriginWH = None # The width and height of the starting image for this zoom
        self.zoomArrow2 = self.canvas.create_image( # Zoom arrow layer 2 (displayed when the mouse enters)
            self.wh[0]-self.zoomSize[0], self.wh[1]-self.zoomSize[1], anchor='nw', image=imgArr)
        self.zoomArrow1 = self.canvas.create_image( # Zoom arrow layer 1 (displayed when the mouse is close)
            self.wh[0]-self.zoomSize[0], self.wh[1]-self.zoomSize[1], anchor='nw', image=imgArr)
        self.canvas.itemconfig(self.zoomArrow1, state=tk.HIDDEN) #Hide layers 1 and 2 by default
        self.canvas.itemconfig(self.zoomArrow2, state=tk.HIDDEN)
        self.moveOriginXY = None # The starting window position of this move

        # Lock related
        imgLock = Asset.getImgTK('lockAlpha48')
        self.isLock = False # The initial value must be False
        self.lockX, self.lockY = 0, 0 # Window offset in lock mode
        self.lockBtn2 = self.canvas.create_image( # Lock icon layer 2 (displayed when mouse enters)
            0, 0, anchor='nw', image=imgLock)
        self.lockBtn1 = self.canvas.create_image( # Lock icon layer 1 (displayed when the mouse is close)
            0, 0, anchor='nw', image=imgLock)
        self.canvas.itemconfig(self.lockBtn1, state=tk.HIDDEN) #Hide layers 1 and 2 by default
        self.canvas.itemconfig(self.lockBtn2, state=tk.HIDDEN)

        # Bind event
        self.win.bind('<Enter>', self.__onWinEnter) # Mouse enters the window
        self.win.bind('<Leave>', self.__onWinLeave) # Mouse leaves the window
        self.canvas.bind('<ButtonPress-1>', self.__onCanvasPress) # Press the canvas
        self.canvas.bind('<ButtonRelease-1>', self.__onCanvasRelease) # Release the canvas
        self.canvas.bind('<B1-Motion>', self.__onCanvasMotion) # Drag the canvas
        self.canvas.bind('<MouseWheel>', self.__onMouseWheel) # Wheel zoom or transparency adjustment
        # 鼠标进入和离开缩放按钮
        self.canvas.tag_bind(self.zoomArrow1, '<Enter>', self.__onZoomEnter)
        self.canvas.tag_bind(self.zoomArrow1, '<Leave>', self.__onZoomLeave)
        # 鼠标进入、离开锁定按钮
        self.canvas.tag_bind(self.lockBtn1, '<Enter>', self.__onLockEnter)
        self.canvas.tag_bind(self.lockBtn1, '<Leave>', self.__onLockLeave)

        # Bind shortcut keys
        self.win.bind('<Return>', self.__ocr) # Enter: OCR
        self.win.bind('<Control-s>', self.__saveImage) # Ctrl+S: Save
        self.win.bind('<Control-c>', self.__copyImage) # Ctrl+C: Copy the image
        self.win.bind('<Escape>', self.__onClose) # Esc: Close the window
        # Ctrl+T and ctrl+L: Lock & Pin
        self.win.bind('<Control-t>', lambda *e: self.__switchLock(0))
        self.win.bind('<Control-l>', lambda *e: self.__switchLock(0))

        # 初始处理
        def start():  # 展开
            self.win.attributes('-topmost', 1) # Pop to the top
            if not Config.get('isWindowTop'): # Follow the main window settings
                self.win.attributes('-topmost', 0) # Unlock topmost
            self.win.focus() # The window gets focus
        self.win.after(200, start)
        setInitialSizeAndPosition
        if initPos: # Initial value has been set
            x, y, w, h = initPos # Unpack tuple
        else: # If the initial value is not set, it is determined by the mouse position.
            x, y = Hotkey.getMousePos() # Get the mouse position
            w, h = self.wh[0], self.wh[1] # Window size = image length and width
            x, y = x-w//2, y-h//2 # Move the center of the window to the mouse position
        self.win.geometry(f'+{x}+{y}') # Set the initial position
        self.win.update() # You must update it first and then set the size, otherwise the height of the menu bar will be eaten
        self.__resize(w, h) # Set the initial size

    # ============================== 事件 ==============================

    def __onWinEnter(self, e=None):  # 鼠标进入窗口
        if self.isLock:  # 锁定状态：显示解锁图标
            self.canvas.itemconfig(self.lockBtn1, state=tk.NORMAL)
        else:  # 非锁定状态：显示缩放图标
            self.canvas.itemconfig(self.zoomArrow1, state=tk.NORMAL)

    def __onWinLeave(self, e=None):  # 鼠标离开窗口
        self.canvas.itemconfig(self.zoomArrow1, state=tk.HIDDEN)
        self.canvas.itemconfig(self.lockBtn1, state=tk.HIDDEN)

    def __canvasFunc(self, e, zoomFunc, moveFunc, lockFunc=None):  # 根据鼠标处于画布哪个位置，执行相应方法
        ids = self.canvas.find_withtag(tk.CURRENT)  # 获取当前鼠标位置的元素
        if self.zoomArrow1 in ids:  # 若是缩放按钮
            zoomFunc(e)
        elif self.lockBtn1 in ids and lockFunc:  # 若是锁定按钮
            lockFunc(e)
        else:  # 若是本体
            moveFunc(e)

    def __onCanvasPress(self, e=None):  # 按下画布
        self.__canvasFunc(e, zoomFunc=self.__onZoomPress,
                          moveFunc=self.__onMovePress,
                          lockFunc=self.__onClickUnlock)

    def __onCanvasRelease(self, e=None):  # 松开画布
        self.__canvasFunc(e, zoomFunc=self.__onZoomRelease,
                          moveFunc=self.__onMoveRelease)

    def __onCanvasMotion(self, e=None):  # 拖拽画布
        if self.isLock:
            return
        self.__canvasFunc(e, zoomFunc=self.__onZoomMotion,
                          moveFunc=self.__onMoveMotion)

    def __onZoomEnter(self, e=None):  # 鼠标进入缩放按钮
        if self.isLock:
            return
        self.canvas.itemconfig(self.zoomArrow2, state=tk.NORMAL)  # 显示2层图标
        self.canvas.config(cursor='sizing')  # 改变光标为缩放箭头

    def __onZoomLeave(self, e=None):  # 鼠标离开缩放按钮
        self.canvas.itemconfig(self.zoomArrow2, state=tk.HIDDEN)
        self.canvas.config(cursor='')  # 改变光标为正常

    def __onZoomPress(self, e=None):  # 按下缩放按钮
        self.mouseOriginXY = (e.x_root, e.y_root)
        self.zoomOriginWH = self.wh  # 读取宽高起点

    def __onZoomRelease(self, e=None):  # 松开缩放按钮
        self.mouseOriginXY = None

    def __onZoomMotion(self, e=None):  # 拖拽缩放按钮
        if self.isLock:
            return
        dx = e.x_root-self.mouseOriginXY[0]  # 离原点的移动量
        dy = e.y_root-self.mouseOriginXY[1]
        nw, nh = self.zoomOriginWH[0]+dx, self.zoomOriginWH[1]+dy  # 计算大小设定
        if self.ratio > RatioThreshold:  # 图像 w 过大，忽视鼠标竖向移动
            nh = 0
        elif self.ratio < 1/RatioThreshold:  # 图像 h 过大，忽视鼠标横向移动
            nw = 0
        self.__resize(nw, nh)  # 重置图片大小

    def __onMovePress(self, e=None):  # 按下移动区域
        self.mouseOriginXY = (e.x_root, e.y_root)  # 必须用_root，排除窗口相对移动的干扰
        self.moveOriginXY = (self.win.winfo_x(), self.win.winfo_y())

    def __onMoveRelease(self, e=None):  # 松开移动区域
        self.mouseOriginXY = None
        self.moveOriginXY = None

    def __onMoveMotion(self, e=None):  # 拖拽移动区域
        if self.isLock:
            return
        dx = e.x_root-self.mouseOriginXY[0]  # 离原点的移动量
        dy = e.y_root-self.mouseOriginXY[1]
        nx, ny = self.moveOriginXY[0]+dx, self.moveOriginXY[1]+dy  # 计算位置设定
        self.win.geometry(f'+{nx}+{ny}')  # 移动窗口

    def __onLockEnter(self, e=None):  # 进入解锁按钮
        if not self.isLock:
            return
        self.canvas.itemconfig(self.lockBtn2, state=tk.NORMAL)  # 显示2层图标
        self.canvas.config(cursor='hand2')  # 改变光标为手指

    def __onLockLeave(self, e=None):  # 离开解锁按钮
        self.canvas.itemconfig(self.lockBtn2, state=tk.HIDDEN)
        self.canvas.config(cursor='')  # 改变光标为正常

    def __onClickUnlock(self, e=None):  # 单击解锁
        self.__switchLock(-1)

    def __onMouseWheel(self, e=None):  # 滚轮
        if self.isLock:
            return
        if e.state == 0:  # 什么都不按，缩放
            step = 30
            s = step if e.delta > 0 else -step
            w = self.wh[0]+s
            self.__resize(w, 0)
        else:  # 按下任何修饰键（Ctrl、Shift等），调整透明度
            step = 0.1
            s = step if e.delta > 0 else -step
            alpha = self.win.attributes('-alpha')
            a = alpha+s
            if a < 0.3:
                a = 0.3
            if a > 1:
                a = 1
            self.win.attributes('-alpha', a)

    # ============================== 功能 ==============================

    def __resize(self, w, h):  # 重设图片和窗口大小。应用w或h中按图片比例更大的一个值。
        if h <= 0:  # 防止除零
            h = 1
        # 适应w或h中比例更大的一个
        if w/h > self.ratio:
            h = int(w/self.ratio)  # w更大，则应用w，改变h
        else:
            w = int(h*self.ratio)  # h更大，则应用h，改变w
        # 防止窗口大小超出屏幕
        if w > self.win.winfo_screenwidth()-MaxSizeMargin:
            w = self.win.winfo_screenwidth()-MaxSizeMargin
            h = int(w/self.ratio)
        if h > self.win.winfo_screenheight()-MaxSizeMargin:
            h = self.win.winfo_screenheight()-MaxSizeMargin
            w = int(h*self.ratio)
        # 最小大小
        if w < MinSize and h < MinSize:
            if self.ratio > 1:  # 图像宽更大，则防止窗口宽度过小
                w = MinSize
                h = int(w/self.ratio)
            else:  # 高同理
                h = MinSize
                w = int(h*self.ratio)

        self.wh = (w, h)
        # 生成并设定缩放后的图片
        resizedImg = self.imgPIL.resize((w, h), Image.BILINEAR)
        self.imgTK = ImageTk.PhotoImage(resizedImg)
        self.canvas.itemconfigure(self.imgCanvas, image=self.imgTK)
        self.win.geometry(f'{w}x{h}')  # 缩放窗口
        # 移动缩放按钮
        ax, ay = w-self.zoomSize[0], h-self.zoomSize[1]
        self.canvas.coords(self.zoomArrow1, ax, ay)
        self.canvas.coords(self.zoomArrow2, ax, ay)

    def __switchLock(self, flag=0):  # 切换：锁定/解锁。
        # flag=0：切换。>0：锁定。<0：解锁。
        if flag == 0:
            self.isLock = not self.isLock
        elif flag > 0:
            self.isLock = True
        else:
            self.isLock = False

        winx, winy = self.win.winfo_x(), self.win.winfo_y()  # 当前相对位置
        self.__onWinLeave()
        if self.isLock:  # 启用锁定
            rootx, rooty = self.win.winfo_rootx(), self.win.winfo_rooty()  # 原本的绝对位置
            self.win.attributes('-topmost', 1)  # 窗口置顶
            self.win.config(menu='')  # 移除菜单栏
            self.win.overrideredirect(True)  # 将窗口设置为无边框模式
            self.canvas.config(borderwidth=1)  # 添加画布边框
            self.win.update()  # 刷新一下
            # 移动窗口，补偿菜单和边框消失的偏移
            self.lockX, self.lockY = self.win.winfo_rootx()-rootx, self.win.winfo_rooty()-rooty
            self.win.geometry(f'+{winx-self.lockX}+{winy-self.lockY}')
        else:  # 解锁
            self.canvas.itemconfig(self.zoomArrow1, state=tk.NORMAL)
            self.win.attributes('-topmost', 0)  # 取消置顶
            self.win.config(menu=self.menubar)  # 恢复菜单栏
            self.win.overrideredirect(False)  # 取消无边框模式
            self.canvas.config(borderwidth=0)  # 取消画布边框
            self.win.update()  # 刷新一下
            # 移动窗口，补偿菜单和边框恢复的偏移
            self.win.geometry(f'+{winx+self.lockX}+{winy+self.lockY}')

    def __ocr(self, e=None):
        self.__copyImage()
        Config.main.runClipboard()

    def __saveImage(self, e=None):
        # 打开文件选择对话框
        now = time.strftime("%Y-%m-%d %H%M%S", time.localtime())
        defaultFileName = f'屏幕截图 {now}.png'
        filePath = tk.filedialog.asksaveasfilename(
            initialfile=defaultFileName,
            defaultextension='.png',
            filetypes=[('PNG Image', '*.png')],
            title='保存图片'
        )

        if filePath:
            # 将 PIL.Image 对象保存为 PNG 文件
            self.imgPIL.save(filePath, format='PNG')

    def __copyImage(self, e=None):
        try:
            OpenClipboard()  # 打开剪贴板
            EmptyClipboard()  # 清空剪贴板
            SetClipboardData(CF_DIB, self.imgData)  # 写入
        except Exception as err:
            Notify('位图无法写入剪贴板', f'{err}')
        finally:
            try:
                CloseClipboard()  # 关闭
            except Exception as err:
                Notify('无法关闭剪贴板', f'{err}')

    def __onClose(self, e=None):
        self.imgTK = None  # 删除图片对象，释放内存
        self.win.destroy()  # 关闭窗口

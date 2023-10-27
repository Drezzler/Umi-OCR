from utils.logger import GetLog
from utils.config import Config, RunModeFlag
from ocr.api_ppocr_json import OcrAPI
from ocr.engine_ram_optimization import OcrEngRam

import os
import time
import asyncio
import threading
from operator import eq
from enum import Enum

Log = GetLog()


class EngFlag(Enum):
    '''engineRunningStatusFlag'''
    none = 0 # Not running
    initing = 1 # Starting
    waiting = 2 # on standby
    running = 3 # Working


class MsnFlag(Enum):
    '''batchTaskStatusFlag'''
    none = 0 # Not running
    initing = 1 # Starting
    running = 2 # Working
    stopping = 3 # Stopping


class OcrEngine:
    '''OCR engine, including various operation methods'''

    def __init__(self):
        # self.__initVar() # __initVar cannot be used and self.setEngFlag() cannot be called because there is no guarantee that the main tk has started the event loop.
        self.__ocrInfo = () # Record previous OCR parameters
        self.__ramTips = '' #Memory usage tips
        self.__runMissionLoop = None # Batch-identified event loop
        self.ocr = None # OCR API object
        self.winSetRunning = None
        self.engFlag = EngFlag.none
        self.msnFlag = MsnFlag.none
        OcrEngRam.init(self.restart, self.getEngFlag, EngFlag) # Memory optimization·initialization, passing in interface

    def __initVar(self):
        self.__ocrInfo = () # Record previous OCR parameters
        self.__ramTips = '' #Memory usage tips
        self.ocr = None # OCR API object
        # self.msnFlag = MsnFlag.none # The task status cannot be changed here. The engine may have been turned off and the task thread is still continuing.

    def __setEngFlag(self, engFlag):
        '''Update engine status and notify the main window'''
        self.engFlag = engFlag
        if self.ocr and Config.get('isDebug'):
            if engFlag == EngFlag.waiting:  # 刷新内存占用
                self.__ramTips = f'（内存：{self.ocr.getRam()}MB）'
        msg = {
            EngFlag.none: 'Close',
            EngFlag.initing: 'Starting',
            EngFlag.waiting: f'waiting{self.__ramTips}',
            EngFlag.running: f'work{self.__ramTips}',
        }.get(engFlag, f'未知（{engFlag}）')
        isTkUpdate = False
        if engFlag == EngFlag.initing:  # 启动中，刷新一下UI
            isTkUpdate = True
        Config.set('ocrProcessStatus', msg, isTkUpdate)  # 设置
        # Log.info(f'ENGINE ⇒ {engFlag}')

    def getEngFlag(self):
        return self.engFlag

    def __setMsnFlag(self, msnFlag):
        '''Update task status and notify the main window'''
        self.msnFlag = msnFlag
        if self.winSetRunning:
            self.winSetRunning(msnFlag)
        # Log.info(f'任务 ⇒ {msnFlag}')

    @staticmethod
    def __tryFunc(func, *e):
        '''TRY TO EXECUTE FUNC'''
        if func:
            try:
                func(*e)
            except Exception as e:
                errMsg = f'调用函数 {str(func)} 异常： {e}'
                Log.error(errMsg)
                Config.main.panelOutput(errMsg+'\n')

    def start(self):
        '''启动引擎。若引擎已启动，且参数有更新，则重启。'''
        if self.engFlag == EngFlag.initing:  # 正在初始化中，严禁重复初始化
            return
        # 检查引擎路径
        ocrToolPath = Config.get('ocrToolPath')
        if not os.path.isfile(ocrToolPath):
            raise Exception(
                f'未在以下路径找到引擎组件\n【{ocrToolPath}】\n\n请将引擎组件【PaddleOCR-json】文件夹放置于指定路径！')
        # 获取静态参数
        ang = ' -cls=1 -use_angle_cls=1' if Config.get('isOcrAngle') else ''
        limit = f" -limit_type={Config.get('ocrLimitMode').get(Config.get('ocrLimitModeName'),'min')} -limit_side_len={Config.get('ocrLimitSize')}"
        staticArgs = f"{ang}{limit}\
 -cpu_threads={Config.get('ocrCpuThreads')}\
 -enable_mkldnn={Config.get('isOcrMkldnn')}\
 {Config.get('argsStr')}"  # 静态启动参数字符串。注意每个参数前面的空格
        # 整合最新OCR参数
        info = (
            ocrToolPath,  # 识别器路径
            Config.get('ocrConfig')[Config.get(
                'ocrConfigName')]['path'],  # 配置文件路径
            staticArgs,  # 启动参数
        )
        isUpdate = not eq(info, self.__ocrInfo)  # 检查是否有变化

        if self.ocr:  # OCR进程已启动
            if not isUpdate:  # 无变化则放假
                return
            self.stop(True)  # 有变化则先停止OCR进程再启动。传入T表示是在重启，无需中断任务。

        self.__ocrInfo = info  # 记录参数。必须在stop()之后，以免被覆盖。
        try:
            Log.info(f'启动引擎，参数：{info}')
            self.__setEngFlag(EngFlag.initing)  # 通知启动中
            self.ocr = OcrAPI(*self.__ocrInfo, initTimeout=Config.get('ocrInitTimeout'))  # 启动引擎
            # 检查启动引擎这段时间里，引擎有没有被叫停
            if not self.engFlag == EngFlag.initing:  # 状态被改变过了
                Log.info(f'初始化后，引擎被叫停！{self.engFlag}')
                self.stop()
                return
            self.__setEngFlag(EngFlag.waiting)  # 通知待命
        except Exception as e:
            self.stop()
            raise

    def stop(self, isRestart=False):
        '''立刻终止引擎。isRE为T时表示这是在重启，无需中断任务。'''
        if (self.msnFlag == MsnFlag.initing or self.msnFlag == MsnFlag.running)\
                and not self.engFlag == EngFlag.none and not isRestart:
            Log.info(f'引擎stop，停止任务！')
            self.__setMsnFlag(MsnFlag.stopping)  # 设任务需要停止
        if hasattr(self.ocr, 'stop'):
            self.ocr.stop()
        del self.ocr
        self.ocr = None
        self.__setEngFlag(EngFlag.none)  # 通知关闭
        self.__initVar()

    def stopByMode(self):
        '''根据配置模式决定是否停止引擎'''
        if self.msnFlag == MsnFlag.initing or self.msnFlag == MsnFlag.running\
                and not self.engFlag == EngFlag.none:
            self.__setMsnFlag(MsnFlag.stopping)  # 设任务需要停止
        n = Config.get('ocrRunModeName')
        modeDict = Config.get('ocrRunMode')
        if n in modeDict.keys():
            mode = modeDict[n]
            if mode == RunModeFlag.short:  # 按需关闭
                self.stop()

    def restart(self):
        '''重启引擎，释放内存'''
        self.stop(True)
        self.start()

    def run(self, path):
        '''执行单张图片识别，输入路径，返回字典'''
        if not self.ocr:
            self.__setEngFlag(EngFlag.none)  # 通知关闭
            return {'code': 404, 'data': f'引擎未在运行'}
        OcrEngRam.runBefore(ram=self.ocr.getRam())  # 内存优化·前段
        self.__setEngFlag(EngFlag.running)  # 通知工作
        data = self.ocr.run(path)
        # 有可能因为提早停止任务或关闭软件，引擎被关闭，OCR.run提前出结果
        # 此时 engFlag 已经被主线程设为 none，如果再设waiting可能导致bug
        # 所以检测一下是否还是正常的状态 running ，没问题才通知待命
        if self.engFlag == EngFlag.running:
            self.__setEngFlag(EngFlag.waiting)  # 通知待命
        OcrEngRam.runAfter()  # 内存优化·后段
        return data

    def runMission(self, paths, msn):
        '''Recognize multiple pictures in batches, asynchronously. If the engine does not start, it will start automatically. \n
        paths: path\n
        msn: Tasker object, a derived class of Msn, must contain onStart|onGet|onStop|onError four methods'''
        if not self.msnFlag == MsnFlag.none: # Running
            Log.error(f'The next round of tasks started before the existing task was completed')
            raise Exception('Existing tasks have not ended')

        self.winSetRunning = Config.main.setRunning # Set the running status interface
        self.__setMsnFlag(MsnFlag.initing) # Set task initialization

        def runLoop(): # Start event loop
            asyncio.set_event_loop(self.__runMissionLoop)
            self.__runMissionLoop.run_forever()

        #Create an event loop under the current thread
        self.__runMissionLoop = asyncio.new_event_loop()
        # Start a new thread and start the event loop in the new thread
        threading.Thread(target=runLoop).start()
        # The event loop continues to wander and execute in the new thread
        asyncio.run_coroutine_threadsafe(self.__runMission(
            paths, msn
        ), self.__runMissionLoop)

    async def __runMission(self, paths, msn):
        '''Recognize images in batches in a new thread. It is safe to update the UI in this thread. '''

        num = {
            'all': len(paths), # all quantities
            'now': 1, # Current processing sequence number
            'index': 0, # Current index
            'succ': 0, # Number of successes
            'err': 0, # Number of failures
            'exist': 0, #The number of words in success
            'none': 0, #The number of successes without text
            'time': 0, #Total time since execution
            'timeNow': 0, # The time taken for this round
        }

        def close():  # stop
            try:
                self.__runMissionLoop.stop() # Close the asynchronous event loop
            except Exception as e:
                Log.error(f'Task thread failed to close the task event loop: {e}')
            self.stopByMode() # Close the OCR process on demand
            self.__tryFunc(msn.onStop, num)
            self.__setMsnFlag(MsnFlag.none) # Set the task to stop
            Log.info(f'Task close!')

        # 启动OCR引擎，批量任务初始化 =========================
        try:
            self.start()  # 启动或刷新引擎
        except Exception as e:
            Log.error(f'批量任务启动引擎失败：{e}')
            self.__tryFunc(msn.onError, num, f'无法启动引擎：{e}')
            close()
            return
        timeStart = time.time()  # 启动时间
        timeLast = timeStart  # 上一轮结束时间

        # 检查启动引擎这段时间里，任务有没有被叫停 =========================
        if self.msnFlag == MsnFlag.stopping:  # 需要停止
            close()
            return
        # 主窗UI和任务处理器初始化 =========================
        self.__setMsnFlag(MsnFlag.running)  # 设任务运行
        self.__tryFunc(msn.onStart, num)

        # 正式开始任务 =========================
        for path in paths:
            if self.msnFlag == MsnFlag.stopping:  # 需要停止
                close()
                return
            isAddErr = False
            try:
                data = self.run(path)  # 调用图片识别
                # 刷新时间
                timeNow = time.time()  # 本轮结束时间
                num['time'] = timeNow-timeStart
                num['timeNow'] = timeNow-timeLast
                timeLast = timeNow
                # 刷新量
                if data['code'] == 100:
                    num['succ'] += 1
                    num['exist'] += 1
                elif data['code'] == 101:
                    num['succ'] += 1
                    num['none'] += 1
                else:
                    num['err'] += 1
                    isAddErr = True
                    # 若设置了进程按需关闭，中途停止任务会导致进程kill，本次识别失败
                    # 若设置了进程后台常驻，中途停止任务会让本次识别完再停止任务
                    # 这些都是正常的（设计中的）
                    # 但是，引擎进程意外关闭导致图片识别失败，则是不正常的；所以不检测engFlag
                    if self.msnFlag == MsnFlag.stopping:  # 失败由强制停止引擎导致引起
                        data['data'] = '这是正常情况。中途停止任务、关闭引擎，导致本张图片未识别完。'
                # 调用取得事件
                self.__tryFunc(msn.onGet, num, data)
            except Exception as e:
                Log.error(f'任务线程 OCR失败： {e}')
                if not isAddErr:
                    num['err'] += 1
                continue
            finally:
                num['now'] += 1
                num['index'] += 1

        close()


OCRe = OcrEngine()  # 引擎单例

# Batch Path Task Processor

from utils.config import Config
from ui.win_notify import Notify  # 通知弹窗
from ocr.engine import MsnFlag
from ocr.msn import Msn
# 输出器
from ocr.output_panel import OutputPanel
from ocr.output_txt import OutputTxt
from ocr.output_separate_txt import OutputSeparateTxt
from ocr.output_md import OutputMD
from ocr.output_jsonl import OutputJsonl
# 文块处理器
from ocr.tbpu.ignore_area import TbpuIgnoreArea

import time
import os

from utils.logger import GetLog
Log = GetLog()


class MsnBatch(Msn):

    # __init__ Initialized in the main thread, other methods are called in the child thread
    def __init__(self):
        # Get the interface
        self.progressbar = Config.main.progressbar # Progress bar component
        self.batList = Config.main.batList # Picture list
        self.setTableItem = Config.main.setTableItem # Set the main table interface
        self.setRunning = Config.main.setRunning # Set the running status interface
        self.clearTableItem = Config.main.clearTableItem # Clean up the main table interface
        # Get value
        self.isDebug = Config.get('isDebug') # Whether to output debugging
        self.isIgnoreNoText = Config.get("isIgnoreNoText") # Whether to ignore pictures without words
        self.areaInfo = Config.get("ignoreArea") # Ignore area
        self.ocrToolPath = Config.get("ocrToolPath") # Recognizer path
        self.configPath = Config.get("ocrConfig")[Config.get( # Configuration file path
            "ocrConfigName")]['path']
        self.argsStr = Config.get("argsStr") # Startup parameters
        # Initialize the exporter
        outputPanel = OutputPanel() # Output to panel
        self.outputList = [outputPanel]
        if Config.get("isOutputTxt"): # Output to txt
            self.outputList.append(OutputTxt())
        if Config.get("isOutputMD"): # Output to markdown
            self.outputList.append(OutputMD())
        if Config.get("isOutputJsonl"): # Output to jsonl
            self.outputList.append(OutputJsonl())
        if Config.get("isOutputSeparateTxt"): # Output to separate txt
            self.outputList.append(OutputSeparateTxt())
        # Initialize text block processor
        self.procList = []
        if Config.get("ignoreArea"): # Ignore area
            self.procList.append(TbpuIgnoreArea())
        tbpuClass = Config.get('tbpu').get( # Other text block processors
            Config.get('tbpuName'), None)
        if tbpuClass:
            self.procList.append(tbpuClass())

        Log.info(f'Batch text processor initialization completed!')

    def __output(self,  type_, *data):  # 输出字符串
        ''' type_ Optional values:
        none: No modifications will be made
        img: image result
        text: text
        debug: debugging information
        '''
        for output in self.outputList:
            if type_ == 'none':
                output.print(*data)
            elif type_ == 'img':
                output.img(*data)
            elif type_ == 'text':
                output.text(*data)
            elif type_ == 'debug':
                output.debug(*data)

    def onStart(self, num):
        Log.info('msnB: onStart')
        #Reset progress prompt
        self.progressbar["maximum"] = num['all']
        self.progressbar["value"] = 0
        Config.set('tipsTop1', f'0s 0/{num["all"]}')
        Config.set('tipsTop2', f'0%')
        Config.main.win.update() # Refresh progress
        self.clearTableItem() # Clear table parameters
        # Output initial information
        startStr = f"\nTask start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}\n\n "
        self.__output('text', startStr)
        # Output debug information of each block processor
        if self.isDebug:
            debugStr = f' Enables output of debug information. \nEngine path: [{self.ocrToolPath}]\nConfiguration file path: [{self.configPath}]\nStartup parameters: [{self.argsStr}]\n'
            if self.procList:
                for proc in self.procList:
                    debugStr += proc.getInitInfo()
                debugStr += '\n'
            else:
                debugStr += 'No block post-processing added\n'
            self.__output('debug', debugStr)
        self.setRunning(MsnFlag.running)

    def onGet(self, numData, ocrData):
        # ==================== Analysis block ====================
        textBlockList = [] # text block list
        textDebug = '' #Debug information
        textScore = '' #Confidence information
        imgInfo = self.batList.get(index=numData['index']) # Get image information
        flagNoOut = False
        if ocrData['code'] == 100: # Success
            textBlockList = ocrData['data'] # Get text block
            # Import the block group into each block processor and obtain the output block group
            for proc in self.procList:
                textBlockList, textD = proc.run(textBlockList, imgInfo)
                if textD:
                    textDebug += f'{textD}\n'
            if textBlockList: # The result has text
                # Calculate confidence
                score = 0
                scoreNum = 0
                for tb in textBlockList:
                    score += tb['score']
                    scoreNum += 1
                if scoreNum > 0:
                    score /= scoreNum
                textScore = str(score)
                textDebug += f'Total time spent: {numData["timeNow"]}s Confidence: {textScore}\n'
            else:
                textScore = 'No text'
                textDebug += f'Total time spent: {numData["timeNow"]}s All text has been ignored\n'
                flagNoOut = True
        elif ocrData['code'] == 101: # No text
            textScore = 'No text'
            textDebug += f'Total time spent: {numData["timeNow"]}s No text found in the picture\n'
            flagNoOut = True
        else: # Recognition failed
            #Write error information to the first block
            textBlockList = [{'box': [0, 0, 0, 0, 0, 0, 0, 0], 'score': 0,
                              'text':f' recognition failed, error code: {ocrData["code"]}\nError message: {str(ocrData["data"])}\n'}]
            textDebug += f'Total time spent: {numData["timeNow"]}s recognition failed\n'
            textScore = 'Error'
        # ==================== Output ====================
        if self.isIgnoreNoText and flagNoOut:
            pass # Set not to output images without text
        else:
            Log.info(textDebug)
            self.__output('img', textBlockList, imgInfo, numData, textDebug)
        # ==================== 刷新UI ====================
        # 刷新进度
        self.progressbar["value"] = numData['now']
        Config.set(
            'tipsTop2', f'{round((numData["now"]/numData["all"])*100)}%')
        Config.set(
            'tipsTop1', f'{round(numData["time"], 2)}s  {numData["now"]}/{numData["all"]}')
        # 刷新表格
        self.setTableItem(time=str(numData['timeNow'])[:4],
                          score=textScore[:4], index=numData['index'])

    def onStop(self, num):
        stopStr = f"\n任务结束时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}\n\n"
        self.__output('text', stopStr)
        if Config.get('isOpenExplorer'):  # 打开输出文件夹
            self.outputList[0].openOutputFile()
        if Config.get('isOpenOutputFile'):  # 打开输出文件
            l = len(self.outputList)
            for i in range(1, l):
                self.outputList[i].openOutputFile()
        if Config.get('isNotify'):  # 通知弹窗
            title = f'识别完成，共{num["all"]}张图片'
            msg = '结果未保存到本地文件，请在软件面板查看'
            if Config.get('isOutputTxt') or Config.get('isOutputSeparateTxt') or Config.get('isOutputMD') or Config.get('isOutputJsonl'):
                msg = f'结果保存到：{Config.get("outputFilePath")}'
            Notify(title, msg)
        if Config.get("isOkMission"):  # 计划任务
            Config.set("isOkMission", False)  # 一次性，设回false
            omName = Config.get('okMissionName')
            okMission = Config.get('okMission')
            if omName in okMission.keys() and 'code' in okMission[omName].keys():
                os.system(okMission[omName]['code'])  # 执行cmd语句
        Log.info('msnB: onClose')
        self.setRunning(MsnFlag.none)
        Config.main.gotoTop()

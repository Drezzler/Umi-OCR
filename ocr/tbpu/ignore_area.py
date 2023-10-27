# Block handling: ignore regions
from utils.config import Config
from ocr.tbpu.tbpu import Tbpu
from utils.logger import GetLog

from time import time

Log = GetLog()


class TbpuIgnoreArea(Tbpu):

    def __init__(self):
        self.areaInfo = Config.get('ignoreArea')  # Ignore region information

    def getInitInfo(self):
        return f'''block post-processing: [ignore area]
Applicable resolution: {self.areaInfo["size"]}
Ignore area A: {self.areaInfo["area"][0]}
Identification area: {self.areaInfo["area"][1]}
Ignore area B: {self.areaInfo["area"][2]}
'''

    def run(self, textBlocks, imgInfo):
        '''Input text block group and picture information. Return text block group and debug information string.'''
        timeIn = time()
        # Size mismatch, no need to ignore areas
        if not self.areaInfo['size'][0] == imgInfo['size'][0] or not self.areaInfo['size'][1] == imgInfo['size'][1]:
            return textBlocks, f'[IGNORE AREA] The image size is{self.areaInfo["size"][0]}x{self.areaInfo["size"][1]}，Does not comply with ignore area{imgInfo["size"][0]}x{imgInfo["size"][1]}'

        # Returns whether the rectangular box bPos is within aPos
        def isInBox(aPos0, aPos1, bPos0, bPos1):  # The upper left and lower right corners of the detection frame, the upper left and lower right corners of the person to be tested
            return bPos0[0] >= aPos0[0] and bPos0[1] >= aPos0[1] and bPos1[0] <= aPos1[0] and bPos1[1] <= aPos1[1]

        # Whether to ignore mode B
        def _isModeB_():
            if self.areaInfo['area'][1]: # Need to detect
                for tb in textBlocks: # Traverse each text block
                    for a in self.areaInfo['area'][1]: # Traverse each detection block
                        # If any text block is within the recognition area detection block, return true
                        if isInBox(a[0], a[1], (tb['box'][0][0], tb['box'][0][1]), (tb['box'][2 ][0], tb['box'][2][1])):
                            return True # Jump out of double loop
        isModeB = _isModeB_()
        modeIndex = 2 if isModeB else 0
        modeChar = 'B' if isModeB else 'A'
        fn = 0  # Number of records ignored
        tempList = []
        for tb in textBlocks:
            flag = True # True means it is not ignored
            # Check whether the current text block tb is within any detection block in the modeIndex mode
            for a in self.areaInfo['area'][modeIndex]:
                if isInBox(a[0], a[1], (tb['box'][0][0], tb['box'][0][1]), (tb['box'][2 ][0], tb['box'][2][1])):
                    flag = False # Step on any block, GG
                    break
            if flag: # is not ignored
                tempList.append(tb)
            else:
                fn += 1
        # Return the new text block group and debug string
        return tempList, f'[ignore area] mode {modeChar}: ignore {fn} items, takes {time()-timeIn}s'

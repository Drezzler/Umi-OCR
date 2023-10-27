# Base class for exporters. Output the incoming text to the specified place according to the specified format.

from utils.logger import GetLog

import os

Log = GetLog()


class Output:
    def __init__(self):
        self.outputPath = ''  # Output path

    def print(self, text):
        '''Directly output text'''
        Log.info(f'输出: {text}')

    def openOutputFile(self):
        '''Open output file (folder)'''
        if self.outputPath and os.path.exists(self.outputPath):
            os.startfile(self.outputPath)

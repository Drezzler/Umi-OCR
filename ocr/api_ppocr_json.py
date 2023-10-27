# Call the Python API of PaddleOCR-json.exe
# Project home page:
# https://github.com/hiroi-sora/PaddleOCR-json


import os
import atexit  # 退出处理
import threading
import subprocess  # 进程，管道
from psutil import Process as psutilProcess  # 内存监控
from sys import platform as sysPlatform  # popen静默模式
from json import loads as jsonLoads, dumps as jsonDumps


class OcrAPI:
    """调用OCR"""

    def __init__(self, exePath, configPath="", argsStr="", initTimeout=20):
        """Initialize the recognizer.\n
        :exePath: The path of the recognizer `PaddleOCR_json.exe`. \n
        :configPath: The path to the configuration file `PaddleOCR_json_config_XXXX.txt`. \n
        :argument: startup parameter, string. See parameter description\n
        :initTimeout: Initialization timeout, seconds\n
        `https://github.com/hiroi-sora/PaddleOCR-json#5-%E9%85%8D%E7%BD%AE%E4%BF%A1%E6%81%AF%E8%AF%B4% E6%98%8E`\n
        """
        cwd = os.path.abspath(os.path.join(exePath, os.pardir))  # Get the exe parent folder
        # Process startup parameters
        args = " "
        if argsStr:  # Add user-specified startup parameters
            args += f" {argsStr}"
        if configPath and "config_path" not in args:  # Specify configuration file
            args += f' --config_path="{configPath}"'
        if "use_debug" not in args:  # Turn off debug mode
            args += " --use_debug=0"
        # Set the child process to enable silent mode and not display the console window
        startupinfo = None
        if "win32" in str(sysPlatform).lower():
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = (
                    subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            )
            startupinfo.wShowWindow = subprocess.SW_HIDE
        self.ret = subprocess.Popen(  # Open the pipe
            exePath + args,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # Discard the contents of stderr
            startupinfo=startupinfo,  # Turn on silent mode
        )
        atexit.register(self.stop)  # Execute a forced stop of the child process when the registered program terminates
        self.psutilProcess = psutilProcess(self.ret.pid)  # Process monitoring object

        self.initErrorMsg = f"OCR init fail.\nEngine path: {exePath}\nStartup parameters: {args}"

        # Sub-thread check timeout
        def cancelTimeout():
            checkTimer.cancel()

        def checkTimeout():
            self.initErrorMsg = f"OCR init timeout: {initTimeout}s.\n{exePath}"
            self.ret.kill()  # Close the child process

        checkTimer = threading.Timer(initTimeout, checkTimeout)
        checkTimer.start()

        # Loop reading and check success flag
        while True:
            if not self.ret.poll() == None:  # The child process has exited and initialization failed.
                cancelTimeout()
                raise Exception(self.initErrorMsg)
            # Must be read line by line, so communicate() cannot be used to avoid timeout issues
            initStr = self.ret.stdout.readline().decode("ascii", errors="ignore")
            if "OCR init completed." in initStr:  # Initialization successful
                break
        cancelTimeout()

    def run(self, imgPath):
        """Recognize text in a picture.\n
        :exePath: Image path. \n
        :return: {'code': identification code, 'data': content list or error message string}\n"""
        if not self.ret.poll() == None:
            return {"code": 400, "data": f"子进程已结束。"}
        # wirteStr = imgPath if imgPath[-1] == '\n' else imgPath + '\n'
        writeDict = {"image_dir": imgPath}
        try:  # Convert the input address to an ascii-escaped json string to avoid encoding issues
            wirteStr = jsonDumps(writeDict, ensure_ascii=True, indent=None) + "\n"
        except Exception as e:
            return {"code": 403,
                    "data": f"Failed to convert input dictionary to json. Dictionary: {writeDict} || Error: [{e}]"}
        # Input path
        try:
            self.ret.stdin.write(wirteStr.encode("ascii"))
            self.ret.stdin.flush()
        except Exception as e:
            return {"code": 400,
                    "data": f"Failed to write the image address to the recognizer process, and the child process is suspected to have crashed.{e}"}
        if imgPath[-1] == "\n":
            imgPath = imgPath[:-1]
        # Get the return value
        try:
            getStr = self.ret.stdout.readline().decode("utf-8", errors="ignore")
        except Exception as e:
            return {
                "code": 401,
                "data": f'failed to read the output value of the recognizer process. It is suspected that a non-existent or unrecognizable image "{imgPath}" was passed in. {e}',
            }
        try:
            return jsonLoads(getStr)
        except Exception as e:
            return {
                "code": 402,
                "data": f'tHE recognizer output value failed to deserialize JSON. It is suspected that a non-existent or unrecognizable image "{imgPath}" was passed in. Exception information: {e}. Original content: {getStr}',
            }

    def stop(self):
       self.ret.kill() # Close the child process. Repeated calls by mistake don't seem to have any ill effects

    def getRam(self):
        """返回内存占用，数字，单位为MB"""
        try:
            return int(self.psutilProcess.memory_info().rss / 1048576)
        except Exception as e:
            return -1

    def __del__(self):
        self.stop()
        atexit.unregister(self.stop)  # 移除退出处理

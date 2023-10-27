# 小组件
from utils.config import Config
from utils.logger import GetLog
from utils.hotkey import Hotkey  # 快捷键

import tkinter as tk
from tkinter import ttk

Log = GetLog()


class Widget:

    @staticmethod
    def comboboxFrame(master, name, configDictName, lockWidget=None, width=None):
        '''Add a checkbox frame
        Parent frame | Schema name (description) | Schema name in Config | Lock list'''
        cFrame = tk.Frame(master)
        cFrame.grid_columnconfigure(1, weight=1)
        tk.Label(cFrame, text=name).grid(column=0, row=0, sticky='w')

        modeName = f'{configDictName}Name'
        modeDict = Config.get(configDictName)
        modeNameList = [i for i in modeDict]
        cbox = ttk.Combobox(cFrame, state='readonly', width=width,
                            textvariable=Config.getTK(modeName), value=modeNameList)
        cbox.grid(column=1, row=0, sticky='ew')
        if Config.get(modeName) not in modeNameList:
            cbox.current(0) #Initialize Combobox and configName
        if lockWidget: # Add to lock list
            lockWidget.append( # The normal state is a special value
                {'widget': cbox, 'stateOFnormal': 'readonly'})
        return cFrame

    @staticmethod
    def delHotkey(hotkey):  # 移除已有快捷键
        if hotkey == '':
            return
        try:
            Hotkey.remove(hotkey) # Remove the shortcut key
        except Exception as err: # Little impact. If you call remove without registration, this exception will be reported.
            Log.info(f'shortcut key【{hotkey}】remove error: {err}')

    @staticmethod
    def hotkeyFrame(master, name, configName, func=None, isFix=False, hotkeyCom=None, isAutoBind=False, isCheckBtn=True):
        '''Add a hotkey frame
        Parent frame | Hotkey name (description) | The name of the hotkey in Config | Trigger event |
        Fixed hotkey | Fixed hotkey name | Whether to automatically bind after creation | Display selected control'''

        isHotkey = f'isHotkey{configName}'
        hotkeyName = f'hotkey{configName}'

        def addHotkey(hotkey):  # Register new shortcut keys
            if hotkey == '':
                Config.set(isHotkey, False)
                tk.messagebox.showwarning(
                    'Prompt', f'Please record {name} shortcut key first')
                return
            if callable(func):
                try:
                    Hotkey.add(hotkey, func) # Add shortcut key monitoring
                except ValueError as err:
                    Config.set(isHotkey, False)
                    Config.set(hotkeyName, '')
                    tk.messagebox.showwarning(
                        'Prompt', f'Unable to register shortcut key [{hotkey}]\n\nError message:\n{err}')

        def onRead():  # 当 修改键按下

            def readSucc(hotkey, errmsg=''):  # Recording success callback
                # Show button
                tips.grid()
                btn.grid()
                tips2.grid_remove()
                # fail
                if not hotkey:
                    if isUsing: #Register old button
                        addHotkey(oldHotkey)
                    tk.messagebox.showwarning(
                        'Prompt', f'Cannot modify shortcut keys\n\nError message:\n{errmsg}')
                    return
                # Check and register hotkeys
                if 'esc' in hotkey or hotkey == oldHotkey: # ESC is cancel
                    if isUsing: #Register old button
                        addHotkey(oldHotkey)
                    return
                if isUsing: # New keys need to be registered
                    addHotkey(hotkey)
                Config.set(hotkeyName, hotkey) #Write settings
                Log.info(
                    f'change the shortcut key [{name}] to [{Config.get(hotkeyName)}]')

            tips.grid_remove()
            btn.grid_remove() # Remove button
            tips2.grid() # Display tips
            hFrame.update() # Refresh UI
            isUsing = Config.get(isHotkey)
            oldHotkey = Config.get(hotkeyName)
            if isUsing: # Already registered
                Widget.delHotkey(oldHotkey) # Unregister existing keys first
            Hotkey.read(readSucc) # Record shortcut keys

        def onCheck(): # When the checkbox is pressed
            if isFix:
                hotkey = hotkeyCom
            else:
                hotkey = Config.get(hotkeyName)
            if Config.get(isHotkey): # Registration required
                addHotkey(hotkey) # Register key
            else: # Need to log out
                Widget.delHotkey(hotkey) #Logout button

        hFrame = tk.Frame(master)
        hFrame.grid_columnconfigure(2, weight=1)

        # Title | Shortcut Key Label | Modify
        if isCheckBtn:
            wid = ttk.Checkbutton(hFrame, variable=Config.getTK(isHotkey),
                                text=name, command=onCheck)
        else:
            wid = tk.Label(hFrame, text=name)
        wid.grid(column=0, row=0, sticky='w')

        if isFix: # Fixed combination, no modification
            tk.Label(hFrame, text='modify', fg='gray').grid(
                column=1, row=0, sticky='w')
            tips = tk.Label(hFrame, text=hotkeyCom, justify='center')
            tips.grid(column=2, row=0, sticky="nsew")
        else: # Allow custom modifications
            btn = tk.Label(hFrame, text='modify', cursor='hand2', fg='blue')
            btn.grid(column=1, row=0, sticky='w')
            btn.bind('<Button-1>', lambda *e: onRead())
            tips = tk.Label(hFrame, textvariable=Config.getTK(hotkeyName),
                            justify='center')
            tips.grid(column=2, row=0, sticky="nsew")
        tips2 = tk.Label(hFrame, text='Waiting for input... (Press Esc to cancel)',
                         justify='center', fg='deeppink')
        tips2.grid(column=2, row=0, sticky="nsew")
        tips2.grid_remove() # Hide

        #Initial registration
        if isAutoBind and Config.get(isHotkey): # Registration required
            addHotkey(Config.get(hotkeyName)) # Register key

        return hFrame

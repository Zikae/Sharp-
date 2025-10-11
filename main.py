version = "0.75"

import win32api, win32con, win32gui, win32process, psutil, time, threading, random, winsound, os, json, subprocess, sys, itertools
import dearpygui.dearpygui as dpg
import math
from ctypes import windll, byref, c_ulong, Structure, POINTER, c_void_p, c_long


# Add structures for memory reading
class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]

class MEMORY_BASIC_INFORMATION(Structure):
    _fields_ = [
        ("BaseAddress", c_void_p),
        ("AllocationBase", c_void_p),
        ("AllocationProtect", c_ulong),
        ("RegionSize", c_ulong),
        ("State", c_ulong),
        ("Protect", c_ulong),
        ("Type", c_ulong)
    ]


PAGE_READWRITE = 0x04

class configListener(dict):
    def __init__(self, initialDict):
        for k, v in initialDict.items():
            if isinstance(v, dict):
                initialDict[k] = configListener(v)

        super().__init__(initialDict)

    def __setitem__(self, item, value):
        if isinstance(value, dict):
            _value = configListener(value)
        else:
            _value = value

        super().__setitem__(item, _value)

        try: # Trash way of checking if Sharp class is initialized
            sharpClass
        except:
            while True:
                try:
                    sharpClass
                    break
                except:
                    time.sleep(0.1)
                    pass

        if sharpClass.config["misc"]["saveSettings"]:
            json.dump(sharpClass.config, open(f"{os.environ['LOCALAPPDATA']}\\temp\\{hwid}", "w", encoding="utf-8"), indent=4)

class sharp():
    def __init__(self, hwid: str):
        self.config = {
            "left": {
                "enabled": False,
                "mode": "Hold",
                "bind": 0,
                "averageCPS": 12,
                "randomization": "Normal",
                "onlyWhenFocused": True,
                "breakBlocks": False,
                "RMBLock": False,
                "blockHit": False,
                "blockHitMode": "Auto",
                "blockHitChance": 25,
                "shakeEffect": False,
                "shakeEffectForce": 5,
                "soundPath": "",
                "workInMenus": False,
                "blatant": False,
            },
            "right": {
                "enabled": False,
                "mode": "Hold",
                "bind": 0,
                "averageCPS": 12,
                "randomization": "Normal",
                "onlyWhenFocused": True,
                "LMBLock": False,
                "shakeEffect": False,
                "shakeEffectForce": False,
                "soundPath": "",
                "workInMenus": False,
                "blatant": False
            },
            "recorder": {
                "enabled": False,
                "record": [0.08] 
            },
            "misc": {
                "saveSettings": True,
                "guiHidden": False,
                "bindHideGUI": 0,
                "accentColor": [107, 110, 248],
                "chromaEnabled": False,
                "chromaSpeed": 1.0,
                "theme": "Dark"
            }
        }

        if os.path.isfile(f"{os.environ['LOCALAPPDATA']}\\temp\\{hwid}"):
            try:
                config = json.loads(open(f"{os.environ['LOCALAPPDATA']}\\temp\\{hwid}", encoding="utf-8").read())

                isConfigOk = True
                for key in self.config:
                    if not key in config or len(self.config[key]) != len(config[key]):
                        isConfigOk = False
                        break

                if isConfigOk:
                    if not config["misc"]["saveSettings"]:
                        self.config["misc"]["saveSettings"] = False
                    else:
                        self.config = config
            except:
                pass

        self.config = configListener(self.config)
        self.record = itertools.cycle(self.config["recorder"]["record"])

        # Chroma variables
        self.chroma_running = False
        self.chroma_thread = None
        self.chroma_hue = 0.0

        threading.Thread(target=self.windowListener, daemon=True).start()
        threading.Thread(target=self.leftBindListener, daemon=True).start()
        threading.Thread(target=self.rightBindListener, daemon=True).start()
        threading.Thread(target=self.hideGUIBindListener, daemon=True).start()

        threading.Thread(target=self.leftClicker, daemon=True).start()
        threading.Thread(target=self.rightClicker, daemon=True).start()

        
        if self.config["misc"]["chromaEnabled"]:
            self.start_chroma()

    def calculate_delay(self, average_cps, randomization_level, is_blatant=False):
        """Calculate delay based on randomization level"""
        if is_blatant:
            return 1 / average_cps

        base_delay = 1 / average_cps

        if randomization_level == "None":
            return base_delay
        elif randomization_level == "Normal":
           
            return random.uniform(base_delay * 0.5, base_delay * 1.5)
        elif randomization_level == "Extra":
            
            return random.uniform(base_delay * 0.3, base_delay * 2.0)
        elif randomization_level == "Extra+":
          
            if random.random() < 0.1:  
                return random.uniform(base_delay * 0.1, base_delay * 0.5)
            else:
                return random.uniform(base_delay * 0.2, base_delay * 2.5)
        else:
            return base_delay

    def windowListener(self):
        while True:
            currentWindow = win32gui.GetForegroundWindow()
            self.realTitle = win32gui.GetWindowText(currentWindow)
            self.window = win32gui.FindWindow("LWJGL", None)

            try:
                self.focusedProcess = psutil.Process(win32process.GetWindowThreadProcessId(currentWindow)[-1]).name()
            except:
                self.focusedProcess = ""

            time.sleep(0.5)

    def leftClicker(self):
        while True:
            if not self.config["recorder"]["enabled"]:
                delay = self.calculate_delay(
                    self.config["left"]["averageCPS"],
                    self.config["left"]["randomization"],
                    self.config["left"]["blatant"]
                )
            else:
                delay = float(next(self.record))

            if self.config["left"]["enabled"]:
                if self.config["left"]["mode"] == "Hold" and not win32api.GetAsyncKeyState(0x01) < 0:
                    time.sleep(delay)
                    continue

                if self.config["left"]["RMBLock"]:
                    if win32api.GetAsyncKeyState(0x02) < 0:
                        time.sleep(delay)
                        continue

                if self.config["left"]["onlyWhenFocused"]:
                    if not "java" in self.focusedProcess and not "AZ-Launcher" in self.focusedProcess:
                        time.sleep(delay)
                        continue

                    if not self.config["left"]["workInMenus"]:
                        cursorInfo = win32gui.GetCursorInfo()[1]
                        if cursorInfo > 50000 and cursorInfo < 100000:
                            time.sleep(delay)
                            continue

                if self.config["left"]["onlyWhenFocused"]:
                    threading.Thread(target=self.leftClick, args=(True,), daemon=True).start()
                else:
                    threading.Thread(target=self.leftClick, args=(None,), daemon=True).start()

            time.sleep(delay)

    def leftClick(self, focused):
        if focused != None:
            if self.config["left"]["breakBlocks"]:
                win32api.SendMessage(self.window, win32con.WM_LBUTTONDOWN, 0, 0)
            else:
                win32api.SendMessage(self.window, win32con.WM_LBUTTONDOWN, 0, 0)
                time.sleep(0.02)
                win32api.SendMessage(self.window, win32con.WM_LBUTTONUP, 0, 0)

            
            should_block_hit = False
            if self.config["left"]["blockHit"]:
                if self.config["left"]["blockHitMode"] == "Auto":
                    
                    should_block_hit = random.uniform(0, 1) <= self.config["left"]["blockHitChance"] / 100.0
                elif self.config["left"]["blockHitMode"] == "Manual":
                   
                    if win32api.GetAsyncKeyState(0x02) < 0:
                       
                        should_block_hit = True

            if should_block_hit:
                win32api.SendMessage(self.window, win32con.WM_RBUTTONDOWN, 0, 0)
                time.sleep(0.02)
                win32api.SendMessage(self.window, win32con.WM_RBUTTONUP, 0, 0)
        else:
            if self.config["left"]["breakBlocks"]:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            else:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                time.sleep(0.02)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

            # Handle block hit
            should_block_hit = False
            if self.config["left"]["blockHit"]:
                if self.config["left"]["blockHitMode"] == "Auto":
                    
                    should_block_hit = random.uniform(0, 1) <= self.config["left"]["blockHitChance"] / 100.0
                elif self.config["left"]["blockHitMode"] == "Manual":
                    
                    if win32api.GetAsyncKeyState(0x02) < 0:
                        
                        should_block_hit = True

            if should_block_hit:
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0)
                time.sleep(0.02)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0)

        if self.config["left"]["soundPath"] != "" and os.path.isfile(self.config["left"]["soundPath"]):
            winsound.PlaySound(self.config["left"]["soundPath"], winsound.SND_ASYNC)

        if self.config["left"]["shakeEffect"]:
            currentPos = win32api.GetCursorPos()
            direction = random.randint(0, 3)
            pixels = random.randint(-self.config["left"]["shakeEffectForce"], self.config["left"]["shakeEffectForce"])

            if direction == 0:
                win32api.SetCursorPos((currentPos[0] + pixels, currentPos[1] - pixels))
            elif direction == 1:
                win32api.SetCursorPos((currentPos[0] - pixels, currentPos[1] + pixels))
            elif direction == 2:
                win32api.SetCursorPos((currentPos[0] + pixels, currentPos[1] + pixels))
            elif direction == 3:
                win32api.SetCursorPos((currentPos[0] - pixels, currentPos[1] - pixels))

    def leftBindListener(self):
        while True:
            if win32api.GetAsyncKeyState(self.config["left"]["bind"]) != 0:
                if "java" in self.focusedProcess or "AZ-Launcher" in self.focusedProcess:
                    cursorInfo = win32gui.GetCursorInfo()[1]
                    if cursorInfo > 50000 and cursorInfo < 100000:
                        time.sleep(0.001)
                        continue

                self.config["left"]["enabled"] = not self.config["left"]["enabled"]

                while True:
                    try:
                        dpg.set_value(checkboxToggleLeftClicker, not dpg.get_value(checkboxToggleLeftClicker))
                        break
                    except:
                        time.sleep(0.1)
                        pass

                while win32api.GetAsyncKeyState(self.config["left"]["bind"]) != 0:
                    time.sleep(0.001)

            time.sleep(0.001)

    def rightClicker(self):
        while True:
            delay = self.calculate_delay(
                self.config["right"]["averageCPS"],
                self.config["right"]["randomization"],
                self.config["right"]["blatant"]
            )

            if self.config["right"]["enabled"]:
                if self.config["right"]["mode"] == "Hold" and not win32api.GetAsyncKeyState(0x02) < 0:
                    time.sleep(delay)
                    continue

                if self.config["right"]["LMBLock"]:
                    if win32api.GetAsyncKeyState(0x01) < 0:
                        time.sleep(delay)
                        continue

                if self.config["right"]["onlyWhenFocused"]:
                    if not "java" in self.focusedProcess and not "AZ-Launcher" in self.focusedProcess:
                        time.sleep(delay)
                        continue

                    if not self.config["right"]["workInMenus"]:
                        cursorInfo = win32gui.GetCursorInfo()[1]
                        if cursorInfo > 50000 and cursorInfo < 100000:
                            time.sleep(delay)
                            continue

                if self.config["right"]["onlyWhenFocused"]:
                    threading.Thread(target=self.rightClick, args=(True,), daemon=True).start()
                else:
                    threading.Thread(target=self.rightClick, args=(None,), daemon=True).start()

            time.sleep(delay)

    def rightClick(self, focused):
        if focused != None:
            win32api.SendMessage(self.window, win32con.WM_RBUTTONDOWN, 0, 0)
            time.sleep(0.02)
            win32api.SendMessage(self.window, win32con.WM_RBUTTONUP, 0, 0)
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0)

        if self.config["right"]["soundPath"] != "" and os.path.isfile(self.config["right"]["soundPath"]):
            winsound.PlaySound(self.config["right"]["soundPath"], winsound.SND_ASYNC)

        if self.config["right"]["shakeEffect"]:
            currentPos = win32api.GetCursorPos()
            direction = random.randint(0, 3)
            pixels = random.randint(-self.config["right"]["shakeEffectForce"], self.config["right"]["shakeEffectForce"])

            if direction == 0:
                win32api.SetCursorPos((currentPos[0] + pixels, currentPos[1] - pixels))
            elif direction == 1:
                win32api.SetCursorPos((currentPos[0] - pixels, currentPos[1] + pixels))
            elif direction == 2:
                win32api.SetCursorPos((currentPos[0] + pixels, currentPos[1] + pixels))
            elif direction == 3:
                win32api.SetCursorPos((currentPos[0] - pixels, currentPos[1] - pixels))

    def rightBindListener(self):
        while True:
            if win32api.GetAsyncKeyState(self.config["right"]["bind"]) != 0:
                if "java" in self.focusedProcess or "AZ-Launcher" in self.focusedProcess:
                    cursorInfo = win32gui.GetCursorInfo()[1]
                    if cursorInfo > 50000 and cursorInfo < 100000:
                        time.sleep(0.001)
                        continue

                self.config["right"]["enabled"] = not self.config["right"]["enabled"]

                while True:
                    try:
                        dpg.set_value(checkboxToggleRightClicker, not dpg.get_value(checkboxToggleRightClicker))
                        break
                    except:
                        time.sleep(0.1)
                        pass

                while win32api.GetAsyncKeyState(self.config["right"]["bind"]) != 0:
                    time.sleep(0.001)

            time.sleep(0.001)

    def hideGUIBindListener(self):
        while True:
            if win32api.GetAsyncKeyState(self.config["misc"]["bindHideGUI"]) != 0:
                self.config["misc"]["guiHidden"] = not self.config["misc"]["guiHidden"]

                if not self.config["misc"]["guiHidden"]:
                    win32gui.ShowWindow(guiWindows, win32con.SW_SHOW)
                else:
                    win32gui.ShowWindow(guiWindows, win32con.SW_HIDE)

                while win32api.GetAsyncKeyState(self.config["misc"]["bindHideGUI"]) != 0:
                    time.sleep(0.001)

            time.sleep(0.001)

    # Chroma effect
    def start_chroma(self):
        """Start the chroma color cycling effect"""
        if not self.chroma_running:
            self.chroma_running = True
            self.chroma_thread = threading.Thread(target=self._chroma_loop, daemon=True)
            self.chroma_thread.start()

    def stop_chroma(self):
        """Stop the chroma color cycling effect"""
        self.chroma_running = False
        if self.chroma_thread:
            self.chroma_thread.join(timeout=1.0)
            self.chroma_thread = None

    def _chroma_loop(self):
        """Main chroma color cycling loop"""
        while self.chroma_running:
           
            r, g, b = self.hsv_to_rgb(self.chroma_hue, 1.0, 1.0)
            r, g, b = int(r * 255), int(g * 255), int(b * 255)

            
            self.config["misc"]["accentColor"] = [r, g, b]

            
            self.chroma_hue += 0.01 * self.config["misc"]["chromaSpeed"]
            if self.chroma_hue >= 1.0:
                self.chroma_hue = 0.0

            
            try:
                updateTheme()
            except:
                pass

            
            sleep_time = max(0.01, 0.05 / self.config["misc"]["chromaSpeed"])
            time.sleep(sleep_time)

    def hsv_to_rgb(self, h, s, v):
        """Convert HSV color to RGB"""
        if s == 0.0:
            return v, v, v

        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6

        if i == 0:
            return v, t, p
        elif i == 1:
            return q, v, p
        elif i == 2:
            return p, v, t
        elif i == 3:
            return p, q, v
        elif i == 4:
            return t, p, v
        else:
            return v, p, q

if __name__ == "__main__":
    try:
        if os.name != "nt":
            input("Sharp+ is only working on Windows.")
            os._exit(0)

        
        try:
            (suppost_sid, error) = subprocess.Popen("wmic useraccount where name='%username%' get sid", stdout=subprocess.PIPE, shell=True).communicate()
            sid_lines = suppost_sid.split(b"\n")
            if len(sid_lines) > 1:
                hwid = sid_lines[1].strip().decode()
            else:
                # Fallback HWID if the command fails
                hwid = str(random.randint(100000, 999999))
        except Exception as e:
            hwid = str(random.randint(100000, 999999))

        currentWindow = win32gui.GetForegroundWindow()
        processName = psutil.Process(win32process.GetWindowThreadProcessId(currentWindow)[-1]).name()
        if processName == "cmd.exe" or processName in sys.argv[0]:
            win32gui.ShowWindow(currentWindow, win32con.SW_HIDE)

        sharpClass = sharp(hwid)
        dpg.create_context()

        with dpg.font_registry():
            default_font = dpg.add_font("C:\\Windows\\Fonts\\segoeui.ttf", 15)
            if not os.path.exists("C:\\Windows\\Fonts\\segoeui.ttf"):
                default_font = dpg.add_font("C:\\Windows\\Fonts\\arial.ttf", 15)

        def toggleLeftClicker(id: int, value: bool):
            sharpClass.config["left"]["enabled"] = value

        waitingForKeyLeft = False
        def statusBindLeftClicker(id: int):
            global waitingForKeyLeft

            if not waitingForKeyLeft:
                with dpg.handler_registry(tag="Left Bind Handler"):
                    dpg.add_key_press_handler(callback=setBindLeftClicker)

                dpg.set_item_label(buttonBindLeftClicker, "...")
                waitingForKeyLeft = True

        def setBindLeftClicker(id: int, value: str):
            global waitingForKeyLeft

            if waitingForKeyLeft:
                sharpClass.config["left"]["bind"] = value
                dpg.set_item_label(buttonBindLeftClicker, f"Bind: {chr(value)}")
                dpg.delete_item("Left Bind Handler")
                waitingForKeyLeft = False

        def setLeftMode(id: int, value: str):
            sharpClass.config["left"]["mode"] = value

        def setLeftAverageCPS(id: int, value: int):
            sharpClass.config["left"]["averageCPS"] = value

        def setLeftRandomization(id: int, value: str):
            sharpClass.config["left"]["randomization"] = value

        def setLeftBlockHitMode(id: int, value: str):
            sharpClass.config["left"]["blockHitMode"] = value

        def toggleLeftOnlyWhenFocused(id: int, value:bool):
            sharpClass.config["left"]["onlyWhenFocused"] = value

        def toggleLeftBreakBlocks(id: int, value: bool):
            sharpClass.config["left"]["breakBlocks"] = value

        def toggleLeftRMBLock(id: int, value: bool):
            sharpClass.config["left"]["RMBLock"] = value

        def toggleLeftBlockHit(id: int, value: bool):
            sharpClass.config["left"]["blockHit"] = value

        def setLeftBlockHitChance(id: int, value: int):
            sharpClass.config["left"]["blockHitChance"] = value

        def toggleLeftShakeEffect(id: int, value: bool):
            sharpClass.config["left"]["shakeEffect"] = value

        def setLeftShakeEffectForce(id: int, value: int):
            sharpClass.config["left"]["shakeEffectForce"] = value

        def setLeftClickSoundPath(id: int, value: str):
            sharpClass.config["left"]["soundPath"] = value

        def browseLeftSoundFile():
            with dpg.file_dialog(directory_selector=False, show=True, callback=setLeftSoundFromDialog, height=400):
                dpg.add_file_extension("Sound files (*.wav){.wav}")

        def setLeftSoundFromDialog(sender, app_data):
            if app_data['file_path_name']:
                sharpClass.config["left"]["soundPath"] = app_data['file_path_name']
                dpg.set_value(inputLeftClickSoundPath, app_data['file_path_name'])

        def toggleLeftWorkInMenus(id: int, value: bool):
            sharpClass.config["left"]["workInMenus"] = value

        def toggleLeftBlatantMode(id: int, value: bool):
            sharpClass.config["left"]["blatant"] = value
            if value:
                dpg.configure_item(sliderLeftAverageCPS, max_value=60)
            else:
                dpg.configure_item(sliderLeftAverageCPS, max_value=20)

        def toggleRightClicker(id: int, value: bool):
            sharpClass.config["right"]["enabled"] = value

        waitingForKeyRight = False
        def statusBindRightClicker(id: int):
            global waitingForKeyRight

            if not waitingForKeyRight:
                with dpg.handler_registry(tag="Right Bind Handler"):
                    dpg.add_key_press_handler(callback=setBindRightClicker)

                dpg.set_item_label(buttonBindRightClicker, "...")
                waitingForKeyRight = True

        def setBindRightClicker(id: int, value: str):
            global waitingForKeyRight

            if waitingForKeyRight:
                sharpClass.config["right"]["bind"] = value
                dpg.set_item_label(buttonBindRightClicker, f"Bind: {chr(value)}")
                dpg.delete_item("Right Bind Handler")
                waitingForKeyRight = False

        def setRightMode(id: int, value: str):
            sharpClass.config["right"]["mode"] = value

        def setRightAverageCPS(id: int, value: int):
            sharpClass.config["right"]["averageCPS"] = value

        def setRightRandomization(id: int, value: str):
            sharpClass.config["right"]["randomization"] = value

        def toggleRightOnlyWhenFocused(id: int, value: bool):
            sharpClass.config["right"]["onlyWhenFocused"] = value

        def toggleRightLMBLock(id: int, value: bool):
            sharpClass.config["right"]["LMBLock"] = value

        def toggleRightShakeEffect(id: int, value: bool):
            sharpClass.config["right"]["shakeEffect"] = value

        def setRightShakeEffectForce(id: int, value: int):
            sharpClass.config["right"]["shakeEffectForce"] = value

        def setRightClickSoundPath(id: int, value: str):
            sharpClass.config["right"]["soundPath"] = value

        def browseRightSoundFile():
            with dpg.file_dialog(directory_selector=False, show=True, callback=setRightSoundFromDialog, height=400):
                dpg.add_file_extension("Sound files (*.wav){.wav}")

        def setRightSoundFromDialog(sender, app_data):
            if app_data['file_path_name']:
                sharpClass.config["right"]["soundPath"] = app_data['file_path_name']
                dpg.set_value(inputRightClickSoundPath, app_data['file_path_name'])

        def toggleRightWorkInMenus(id: int, value: bool):
            sharpClass.config["right"]["workInMenus"] = value

        def toggleRightBlatantMode(id: int, value: bool):
            sharpClass.config["right"]["blatant"] = value
            if value:
                dpg.configure_item(sliderRightAverageCPS, max_value=60)
            else:
                dpg.configure_item(sliderRightAverageCPS, max_value=20)

        def toggleRecorder(id: int, value: bool):
            sharpClass.config["recorder"]["enabled"] = value

        recording = False
        def recorder():
            global recording

            recording = True
            dpg.set_value(recordingStatusText, f"Recording: True")

            recorded = []
            start = 0

            while True:
                if not recording:
                    if len(recorded) < 2:
                        recorded[0] = 0.08
                    else:
                        recorded[0] = 0
                        del recorded[-1]

                    sharpClass.config["recorder"]["record"] = recorded
                    sharpClass.record = itertools.cycle(recorded)

                    totalTime = 0
                    for clickTime in recorded:
                        totalTime += float(clickTime)

                    dpg.set_value(averageRecordCPSText, f"Average CPS of previous Record: {round(len(recorded) / totalTime, 2)}")
                    break

                if win32api.GetAsyncKeyState(0x01) < 0:
                    recorded.append(time.time() - start)
                    dpg.set_value(recordingStatusText, f"Recording: True - Recorded clicks: {len(recorded)}")
                    start = time.time()

                    while win32api.GetAsyncKeyState(0x01) < 0:
                        time.sleep(0.001)

        def startRecording():
            if not recording:
                threading.Thread(target=recorder, daemon=True).start()

        def stopRecording():
            global recording
            recording = False
            dpg.set_value(recordingStatusText, f"Recording: False")

        def selfDestruct():
            sharpClass.stop_chroma()
            dpg.destroy_context()

        waitingForKeyHideGUI = False
        def statusBindHideGUI():
            global waitingForKeyHideGUI

            if not waitingForKeyHideGUI:
                with dpg.handler_registry(tag="Hide GUI Bind Handler"):
                    dpg.add_key_press_handler(callback=setBindHideGUI)

                dpg.set_item_label(buttonBindHideGUI, "...")
                waitingForKeyHideGUI = True

        def setBindHideGUI(id: int, value: str):
            global waitingForKeyHideGUI

            if waitingForKeyHideGUI:
                sharpClass.config["misc"]["bindHideGUI"] = value
                dpg.set_item_label(buttonBindHideGUI, f"Bind: {chr(value)}")
                dpg.delete_item("Hide GUI Bind Handler")
                waitingForKeyHideGUI = False

        def toggleSaveSettings(id: int, value: bool):
            sharpClass.config["misc"]["saveSettings"] = value

        def toggleAlwaysOnTop(id: int, value: bool):
            if value:
                win32gui.SetWindowPos(guiWindows, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            else:
                win32gui.SetWindowPos(guiWindows, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

        def updateAccentColor(sender, app_data):
            r = int(app_data[0] * 255)
            g = int(app_data[1] * 255)
            b = int(app_data[2] * 255)
            sharpClass.config["misc"]["accentColor"] = [r, g, b]
            updateTheme()

        def toggleChroma(id: int, value: bool):
            sharpClass.config["misc"]["chromaEnabled"] = value
            if value:
                sharpClass.start_chroma()
            else:
                sharpClass.stop_chroma()

        def setChromaSpeed(id: int, value: float):
            sharpClass.config["misc"]["chromaSpeed"] = value

        def setTheme(sender, app_data):
            sharpClass.config["misc"]["theme"] = app_data
            updateTheme()

        main_theme = None

        def create_theme():
            global main_theme

            accent_color = sharpClass.config["misc"]["accentColor"]
            theme_name = sharpClass.config["misc"]["theme"]

            if theme_name == "Dark":
                bg_color = [40, 40, 40]
                text_color = [255, 255, 255]
                item_bg = [60, 60, 60]
            elif theme_name == "Light":
                bg_color = [240, 240, 240]
                text_color = [0, 0, 0]
                item_bg = [220, 220, 220]
            else:
                bg_color = [40, 40, 40]
                text_color = [255, 255, 255]
                item_bg = [60, 60, 60]

            if main_theme and dpg.does_item_exist(main_theme):
                dpg.delete_item(main_theme)

            main_theme = dpg.add_theme()

            with dpg.theme_component(dpg.mvAll, parent=main_theme):
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 3)
                dpg.add_theme_style(dpg.mvStyleVar_GrabMinSize, 20)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4)

                # colors
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, bg_color)
                dpg.add_theme_color(dpg.mvThemeCol_Text, text_color)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, item_bg)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, [item_bg[0] + 10, item_bg[1] + 10, item_bg[2] + 10])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, accent_color)

                # accent
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, accent_color)
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, accent_color)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, accent_color)
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, accent_color)
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, accent_color)
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, accent_color)
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, accent_color)
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, accent_color)

            return main_theme

        def updateTheme():
            global main_theme
            theme = create_theme()
            dpg.bind_theme(theme)

        dpg.create_viewport(title=f"[v{version}] Sharp+ - Advanced Minecraft Autoclicker", width=1000, height=600)

        with dpg.window(tag="Primary Window"):
            with dpg.tab_bar():
                with dpg.tab(label="Left Clicker"):
                    dpg.add_spacer(width=75)

                    with dpg.group(horizontal=True):
                        checkboxToggleLeftClicker = dpg.add_checkbox(label="Toggle", default_value=sharpClass.config["left"]["enabled"], callback=toggleLeftClicker)
                        buttonBindLeftClicker = dpg.add_button(label="Click to Bind", callback=statusBindLeftClicker)
                        dropdownLeftMode = dpg.add_combo(label="Mode", items=["Hold", "Always"], default_value=sharpClass.config["left"]["mode"], callback=setLeftMode)

                        bind = sharpClass.config["left"]["bind"]
                        if bind != 0:
                            dpg.set_item_label(buttonBindLeftClicker, f"Bind: {chr(bind)}")

                    dpg.add_spacer(width=75)

                    sliderLeftAverageCPS = dpg.add_slider_int(label="Average CPS", default_value=sharpClass.config["left"]["averageCPS"], min_value=1, max_value=20, callback=setLeftAverageCPS)

                    dropdownLeftRandomization = dpg.add_combo(label="Randomization", items=["None", "Normal", "Extra", "Extra+"], default_value=sharpClass.config["left"]["randomization"], callback=setLeftRandomization)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxLeftOnlyWhenFocused = dpg.add_checkbox(label="Only In Game", default_value=sharpClass.config["left"]["onlyWhenFocused"], callback=toggleLeftOnlyWhenFocused)

                    dpg.add_spacer(width=75)

                    checkBoxLeftBreakBlocks = dpg.add_checkbox(label="Break Blocks", default_value=sharpClass.config["left"]["breakBlocks"], callback=toggleLeftBreakBlocks)

                    dpg.add_spacer(width=75)

                    checkboxLeftRMBLock = dpg.add_checkbox(label="RMB-Lock", default_value=sharpClass.config["left"]["RMBLock"], callback=toggleLeftRMBLock)

                    dpg.add_spacer(width=125)

                    checkboxLeftBlockHit = dpg.add_checkbox(label="BlockHit", default_value=sharpClass.config["left"]["blockHit"], callback=toggleLeftBlockHit)
                    sliderLeftBlockHitChance = dpg.add_slider_int(label="BlockHit Chance", default_value=sharpClass.config["left"]["blockHitChance"], min_value=1, max_value=100, callback=setLeftBlockHitChance)
                    dropdownLeftBlockHitMode = dpg.add_combo(label="BlockHit Mode", items=["Auto", "Manual"], default_value=sharpClass.config["left"]["blockHitMode"], callback=setLeftBlockHitMode)

                    dpg.add_spacer(width=125)

                    checkboxLeftShakeEffect = dpg.add_checkbox(label="Shake Effect", default_value=sharpClass.config["left"]["shakeEffect"], callback=toggleLeftShakeEffect)
                    sliderLeftShakeEffectForce = dpg.add_slider_int(label="Shake Effect Force", default_value=sharpClass.config["left"]["shakeEffectForce"], min_value=1, max_value=20, callback=setLeftShakeEffectForce)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    with dpg.group(horizontal=True):
                        inputLeftClickSoundPath = dpg.add_input_text(label="Click Sound Path", default_value=sharpClass.config["left"]["soundPath"], hint="Select a sound file", callback=setLeftClickSoundPath, width=300)
                        buttonBrowseLeftSound = dpg.add_button(label="Browse", callback=browseLeftSoundFile)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxLeftWorkInMenus = dpg.add_checkbox(label="Work in Menus", default_value=sharpClass.config["left"]["workInMenus"], callback=toggleLeftWorkInMenus)
                    checkboxLeftBlatantMode = dpg.add_checkbox(label="Blatant Mode", default_value=sharpClass.config["left"]["blatant"], callback=toggleLeftBlatantMode)

                with dpg.tab(label="Right Clicker"):
                    dpg.add_spacer(width=75)

                    with dpg.group(horizontal=True):
                        checkboxToggleRightClicker = dpg.add_checkbox(label="Toggle", default_value=sharpClass.config["right"]["enabled"], callback=toggleRightClicker)
                        buttonBindRightClicker = dpg.add_button(label="Click to Bind", callback=statusBindRightClicker)
                        dropdownRightMode = dpg.add_combo(label="Mode", items=["Hold", "Always"], default_value=sharpClass.config["right"]["mode"], callback=setRightMode)

                        bind = sharpClass.config["right"]["bind"]
                        if bind != 0:
                            dpg.set_item_label(buttonBindRightClicker, f"Bind: {chr(bind)}")

                    dpg.add_spacer(width=75)

                    sliderRightAverageCPS = dpg.add_slider_int(label="Average CPS", default_value=sharpClass.config["right"]["averageCPS"], min_value=1, max_value=20, callback=setRightAverageCPS)

                    dropdownRightRandomization = dpg.add_combo(label="Randomization", items=["None", "Normal", "Extra", "Extra+"], default_value=sharpClass.config["right"]["randomization"], callback=setRightRandomization)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxRightOnlyWhenFocused = dpg.add_checkbox(label="Only In Game", default_value=sharpClass.config["right"]["onlyWhenFocused"], callback=toggleRightOnlyWhenFocused)

                    dpg.add_spacer(width=75)

                    checkboxRightLMBLock = dpg.add_checkbox(label="LMB-Lock", default_value=sharpClass.config["right"]["LMBLock"], callback=toggleRightLMBLock)

                    dpg.add_spacer(width=75)

                    checkboxRightShakeEffect = dpg.add_checkbox(label="Shake Effect", default_value=sharpClass.config["right"]["shakeEffect"], callback=toggleRightShakeEffect)
                    sliderRightShakeEffectForce = dpg.add_slider_int(label="Shake Effect Force", default_value=sharpClass.config["right"]["shakeEffectForce"], min_value=1, max_value=20, callback=setRightShakeEffectForce)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    with dpg.group(horizontal=True):
                        inputRightClickSoundPath = dpg.add_input_text(label="Click Sound Path", default_value=sharpClass.config["right"]["soundPath"], hint="Select a sound file", callback=setRightClickSoundPath, width=300)
                        buttonBrowseRightSound = dpg.add_button(label="Browse", callback=browseRightSoundFile)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxRightWorkInMenus = dpg.add_checkbox(label="Work in Menus", default_value=sharpClass.config["right"]["workInMenus"], callback=toggleRightWorkInMenus)
                    checkboxRightBlatantMode = dpg.add_checkbox(label="Blatant Mode", default_value=sharpClass.config["right"]["blatant"], callback=toggleRightBlatantMode)

                with dpg.tab(label="Recorder"):
                    dpg.add_spacer(width=75)

                    recorderInfoText = dpg.add_text(default_value="Records your legit way of clicking in order to produce clicks even less detectable by AntiCheat.\nAfter pressing the \"Start\" button, click as if you were in PvP for a few seconds. Then press the \"Stop\" button.\nOnly works for the left click.")

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxRecorderEnabled = dpg.add_checkbox(label="Enabled", default_value=sharpClass.config["recorder"]["enabled"], callback=toggleRecorder)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    with dpg.group(horizontal=True):
                        buttonStartRecording = dpg.add_button(label="Start Recording", callback=startRecording)
                        buttonStopRecording = dpg.add_button(label="Stop Recording", callback=stopRecording)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    averageRecordCPSText = dpg.add_text(default_value="Average CPS of previous Record: ")

                    totalTime = 0
                    for clickTime in sharpClass.config["recorder"]["record"]:
                        totalTime += float(clickTime)

                    dpg.set_value(averageRecordCPSText, f"Average CPS of previous Record: {round(len(sharpClass.config['recorder']['record']) / totalTime, 2)}")

                    recordingStatusText = dpg.add_text(default_value="Recording: ")
                    dpg.set_value(recordingStatusText, f"Recording: {recording}")

                with dpg.tab(label="Misc"):
                    dpg.add_spacer(width=75)

                    with dpg.theme() as red_button_theme:
                        with dpg.theme_component(dpg.mvButton):
                            dpg.add_theme_color(dpg.mvThemeCol_Button, (200, 50, 50))
                            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 80, 80))
                            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (150, 30, 30))

                    buttonSelfDestruct = dpg.add_button(label="Destruct", callback=selfDestruct)
                    dpg.bind_item_theme(buttonSelfDestruct, red_button_theme)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    with dpg.group(horizontal=True):
                        buttonBindHideGUI = dpg.add_button(label="Click to Bind", callback=statusBindHideGUI)
                        hideGUIText = dpg.add_text(default_value="Hide GUI")

                        bind = sharpClass.config["misc"]["bindHideGUI"]
                        if bind != 0:
                            dpg.set_item_label(buttonBindHideGUI, f"Bind: {chr(bind)}")

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    saveSettings = dpg.add_checkbox(label="Save Settings", default_value=sharpClass.config["misc"]["saveSettings"], callback=toggleSaveSettings)

                    dpg.add_spacer(width=75)

                    checkboxAlwaysOnTop = dpg.add_checkbox(label="Always On Top", callback=toggleAlwaysOnTop)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    # Color customization section
                    dpg.add_text("Customization:")
                    dpg.add_spacer(height=10)

                    dpg.add_combo(label="Theme", items=["Dark", "Light"], default_value=sharpClass.config["misc"]["theme"], callback=setTheme)

                    dpg.add_spacer(height=10)

                    accent_color_float = [
                        sharpClass.config["misc"]["accentColor"][0] / 255.0,
                        sharpClass.config["misc"]["accentColor"][1] / 255.0,
                        sharpClass.config["misc"]["accentColor"][2] / 255.0,
                        1.0
                    ]
                    dpg.add_color_edit(label="Accent Color", default_value=accent_color_float, callback=updateAccentColor)
                    dpg.add_text("Change the accent color of the interface")

                    dpg.add_spacer(height=10)

                    # Chroma controls
                    checkboxChroma = dpg.add_checkbox(label="Chroma Effect", default_value=sharpClass.config["misc"]["chromaEnabled"], callback=toggleChroma)
                    sliderChromaSpeed = dpg.add_slider_float(label="Chroma Speed", default_value=sharpClass.config["misc"]["chromaSpeed"], min_value=0.1, max_value=5.0, callback=setChromaSpeed)
                    dpg.add_text("Rainbow color cycling effect for the interface")

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    creditsText = dpg.add_text(default_value="Credits: Bambou (Developer) - Enhanced by Zikae")
                    githubText = dpg.add_text(default_value="https://github.com/Zikae/Sharp-")

        
        updateTheme()

        
        if sharpClass.config["left"]["blatant"]:
            dpg.configure_item(sliderLeftAverageCPS, max_value=60)
        if sharpClass.config["right"]["blatant"]:
            dpg.configure_item(sliderRightAverageCPS, max_value=60)

        dpg.show_viewport()

        guiWindows = win32gui.GetForegroundWindow()

        dpg.setup_dearpygui()
        dpg.set_primary_window("Primary Window", True)
        dpg.start_dearpygui()

        selfDestruct()
    except KeyboardInterrupt:
        sharpClass.stop_chroma()
        os._exit(0)


version = "1.0+"

import win32api, win32con, win32gui, win32process, psutil, time, threading, random, winsound, os, json, subprocess, sys, itertools
import dearpygui.dearpygui as dpg
import math
from ctypes import windll, byref, c_ulong, Structure, POINTER, c_void_p, c_long


#Add structures for memory reading 
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
                "onlyWhenFocused": True,
                "breakBlocks": False,
                "RMBLock": False,
                "blockHit": False,
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
                "onlyWhenFocused": True,
                "LMBLock": False,
                "shakeEffect": False,
                "shakeEffectForce": False,
                "soundPath": "",
                "workInMenus": False,
                "blatant": False
            },
            "aimassist": {
                "enabled": False,
                "bind": 0,
                "clickAim": True,
                "strafeIncrease": False,
                "checkBlockBreak": True,
                "blockBreakWhitelist": "pickaxe,axe,shovel",
                "aimVertically": True,
                "verticalSpeed": 5,
                "horizontalSpeed": 5,
                "maxAngle": 30,
                "distance": 50,
                "limitToItems": False,
                "itemsWhitelist": "sword,bow",
                "targetArea": "Center",
                "targetMode": "Distance"
            },
            "recorder": {
                "enabled": False,
                "record": [0.08] # Default 12 CPS
            },
            "misc": {
                "saveSettings": True,
                "guiHidden": False,
                "bindHideGUI": 0,
                "accentColor": [107, 110, 248],  
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

        # Aim assist variables
        self.aim_target = None
        self.last_mouse_pos = (0, 0)
        self.entity_list = []
        self.local_player = None

        threading.Thread(target=self.windowListener, daemon=True).start()
        threading.Thread(target=self.leftBindListener, daemon=True).start()
        threading.Thread(target=self.rightBindListener, daemon=True).start()
        threading.Thread(target=self.aimAssistBindListener, daemon=True).start()
        threading.Thread(target=self.hideGUIBindListener, daemon=True).start()
        threading.Thread(target=self.aimAssistThread, daemon=True).start() 

        threading.Thread(target=self.leftClicker, daemon=True).start()
        threading.Thread(target=self.rightClicker, daemon=True).start()

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

    # AIM ASSIST IMPLEMENTATION
    def aimAssistThread(self):
        """Main aim assist thread that handles target acquisition and aiming"""
        while True:
            if self.config["aimassist"]["enabled"]:
                
                if self.shouldRunAimAssist():
                    
                    target = self.findBestTarget()
                    if target:
                        self.aimAtTarget(target)

            time.sleep(0.01)  

    def shouldRunAimAssist(self):
        """Check if aim assist should run based on various conditions"""
        
        if not "java" in self.focusedProcess and not "AZ-Launcher" in self.focusedProcess:
            return False

        
        if self.config["aimassist"]["clickAim"] and not win32api.GetAsyncKeyState(0x01) < 0:
            return False

        
        if not self.config["aimassist"].get("workInMenus", False):
            cursorInfo = win32gui.GetCursorInfo()[1]
            if cursorInfo > 50000 and cursorInfo < 100000:
                return False

        
        if self.config["aimassist"]["checkBlockBreak"]:
           
            pass

        return True

    def findBestTarget(self):
        """Find the best target based on configuration"""
        

        
        simulated_entities = self.simulateEntities()

        if not simulated_entities:
            return None

        # Filter by distance
        max_distance = self.config["aimassist"]["distance"]
        valid_entities = [e for e in simulated_entities if e["distance"] <= max_distance]

        if not valid_entities:
            return None

        
        if self.config["aimassist"]["targetMode"] == "Distance":
            return min(valid_entities, key=lambda x: x["distance"])
        elif self.config["aimassist"]["targetMode"] == "Yaw":
            
            return min(valid_entities, key=lambda x: x["angle_diff"])
       

        return valid_entities[0]  

    def simulateEntities(self):
        """Simulate entity positions for demonstration"""
        # This is a placeholder
        entities = []

        # Simulate some entities around the player
        for i in range(5):
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(2, self.config["aimassist"]["distance"])

            entity = {
                "x": math.cos(angle) * distance,
                "y": random.uniform(-1, 2),  
                "z": math.sin(angle) * distance,
                "distance": distance,
                "angle_diff": random.uniform(0, 30),  
                "health": random.uniform(1, 20),
                "type": "mob" if random.random() > 0.5 else "player"
            }
            entities.append(entity)

        return entities

    def aimAtTarget(self, target):
        """Aim at the selected target"""
        
        current_pos = win32api.GetCursorPos()

        
        screen_width, screen_height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)

        
        target_angle_x = math.atan2(target["z"], target["x"]) * 180 / math.pi
        target_angle_y = math.atan2(target["y"], math.sqrt(target["x"]**2 + target["z"]**2)) * 180 / math.pi

        
        horizontal_speed = self.config["aimassist"]["horizontalSpeed"] / 100.0
        vertical_speed = self.config["aimassist"]["verticalSpeed"] / 100.0 if self.config["aimassist"]["aimVertically"] else 0

        
        move_x = target_angle_x * horizontal_speed
        move_y = target_angle_y * vertical_speed if self.config["aimassist"]["aimVertically"] else 0

        
        max_angle = self.config["aimassist"]["maxAngle"]
        move_x = max(-max_angle, min(max_angle, move_x))
        move_y = max(-max_angle, min(max_angle, move_y))

        
        if self.config["aimassist"]["strafeIncrease"]:
            
            if random.random() > 0.7:  # 30% chance of strafing
                move_x *= 1.5
                move_y *= 1.5

        
        if abs(move_x) > 0.1 or abs(move_y) > 0.1:  # Dead zone
            new_x = current_pos[0] + int(move_x)
            new_y = current_pos[1] + int(move_y)

            
            new_x = max(0, min(screen_width - 1, new_x))
            new_y = max(0, min(screen_height - 1, new_y))

            win32api.SetCursorPos((new_x, new_y))

    def leftClicker(self):
        while True:
            if not self.config["recorder"]["enabled"]:
                if self.config["left"]["blatant"]:
                    delay = 1 / self.config["left"]["averageCPS"]
                else:
                    delay = random.random() % (2 / self.config["left"]["averageCPS"])
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

            if self.config["left"]["blockHit"] or (self.config["left"]["blockHit"] and self.config["right"]["enabled"] and self.config["right"]["LMBLock"] and not win32api.GetAsyncKeyState(0x02) < 0):
                if random.uniform(0, 1) <= self.config["left"]["blockHitChance"] / 100.0:
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

            if self.config["left"]["blockHit"] or (self.config["left"]["blockHit"] and self.config["right"]["enabled"] and self.config["right"]["LMBLock"] and not win32api.GetAsyncKeyState(0x02) < 0):
                if random.uniform(0, 1) <= self.config["left"]["blockHitChance"] / 100.0:
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
            if self.config["right"]["blatant"]:
                delay = 1 / self.config["right"]["averageCPS"]
            else:
                delay = random.random() % (2 / self.config["right"]["averageCPS"])

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

    def aimAssistBindListener(self):
        while True:
            if win32api.GetAsyncKeyState(self.config["aimassist"]["bind"]) != 0:
                if "java" in self.focusedProcess or "AZ-Launcher" in self.focusedProcess:
                    cursorInfo = win32gui.GetCursorInfo()[1]
                    if cursorInfo > 50000 and cursorInfo < 100000:
                        time.sleep(0.001)
                        continue

                self.config["aimassist"]["enabled"] = not self.config["aimassist"]["enabled"]

                while True:
                    try:
                        dpg.set_value(checkboxToggleAimAssist, not dpg.get_value(checkboxToggleAimAssist))
                        break
                    except:
                        time.sleep(0.1)
                        pass

                while win32api.GetAsyncKeyState(self.config["aimassist"]["bind"]) != 0:
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

if __name__ == "__main__":
    try:
        if os.name != "nt":
            input("Sharp+ is only working on Windows.")
            os._exit(0)

        # Fixed HWID retrieval with error handling
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
            
            default_font = dpg.add_font("C:\\Windows\\Fonts\\segoeui.ttf", 15)  # Segoe UI font
            
            if not os.path.exists("C:\\Windows\\Fonts\\segoeui.ttf"):
                default_font = dpg.add_font("C:\\Windows\\Fonts\\arial.ttf", 15)  # Arial font

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

        def toggleLeftWorkInMenus(id: int, value: bool):
            sharpClass.config["left"]["workInMenus"] = value

        def toggleLeftBlatantMode(id: int, value: bool):
            sharpClass.config["left"]["blatant"] = value

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

        def toggleRightOnlyWhenFocused(id: int, value: bool):  # Fixed this function
            sharpClass.config["right"]["onlyWhenFocused"] = value

        def toggleRightLMBLock(id: int, value: bool):
            sharpClass.config["right"]["LMBLock"] = value

        def toggleRightShakeEffect(id: int, value: bool):
            sharpClass.config["right"]["shakeEffect"] = value

        def setRightShakeEffectForce(id: int, value: int):
            sharpClass.config["right"]["shakeEffectForce"] = value

        def setRightClickSoundPath(id: int, value: str):
            sharpClass.config["right"]["soundPath"] = value

        def toggleRightWorkInMenus(id: int, value: bool):
            sharpClass.config["right"]["workInMenus"] = value

        def toggleRightBlatantMode(id: int, value: bool):
            sharpClass.config["right"]["blatant"] = value

        # Aim Assist functions
        def toggleAimAssist(id: int, value: bool):
            sharpClass.config["aimassist"]["enabled"] = value

        waitingForKeyAimAssist = False
        def statusBindAimAssist(id: int):
            global waitingForKeyAimAssist

            if not waitingForKeyAimAssist:
                with dpg.handler_registry(tag="Aim Assist Bind Handler"):
                    dpg.add_key_press_handler(callback=setBindAimAssist)

                dpg.set_item_label(buttonBindAimAssist, "...")
                waitingForKeyAimAssist = True

        def setBindAimAssist(id: int, value: str):
            global waitingForKeyAimAssist

            if waitingForKeyAimAssist:
                sharpClass.config["aimassist"]["bind"] = value
                dpg.set_item_label(buttonBindAimAssist, f"Bind: {chr(value)}")
                dpg.delete_item("Aim Assist Bind Handler")
                waitingForKeyAimAssist = False

        def toggleClickAim(id: int, value: bool):
            sharpClass.config["aimassist"]["clickAim"] = value

        def toggleStrafeIncrease(id: int, value: bool):
            sharpClass.config["aimassist"]["strafeIncrease"] = value

        def toggleCheckBlockBreak(id: int, value: bool):
            sharpClass.config["aimassist"]["checkBlockBreak"] = value

        def setBlockBreakWhitelist(id: int, value: str):
            sharpClass.config["aimassist"]["blockBreakWhitelist"] = value

        def toggleAimVertically(id: int, value: bool):
            sharpClass.config["aimassist"]["aimVertically"] = value

        def setVerticalSpeed(id: int, value: int):
            sharpClass.config["aimassist"]["verticalSpeed"] = value

        def setHorizontalSpeed(id: int, value: int):
            sharpClass.config["aimassist"]["horizontalSpeed"] = value

        def setMaxAngle(id: int, value: int):
            sharpClass.config["aimassist"]["maxAngle"] = value

        def setDistance(id: int, value: int):
            sharpClass.config["aimassist"]["distance"] = value

        def toggleLimitToItems(id: int, value: bool):
            sharpClass.config["aimassist"]["limitToItems"] = value

        def setItemsWhitelist(id: int, value: str):
            sharpClass.config["aimassist"]["itemsWhitelist"] = value

        def setTargetArea(id: int, value: str):
            sharpClass.config["aimassist"]["targetArea"] = value

        def setTargetMode(id: int, value: str):
            sharpClass.config["aimassist"]["targetMode"] = value

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
                    if len(recorded) < 2: # Avoid saving a record with 0 click
                        recorded[0] = 0.08
                    else:
                        recorded[0] = 0 # No delay for the first click
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
            else:  # Custom or other themes
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

                # Colors
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, bg_color)
                dpg.add_theme_color(dpg.mvThemeCol_Text, text_color)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, item_bg)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, [item_bg[0] + 10, item_bg[1] + 10, item_bg[2] + 10])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, accent_color)

                # Accent colors
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

        dpg.create_viewport(title=f"[v{version}] Sharp+ - Advanced Minecraft Utility", width=1000, height=600)

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

                    dpg.add_spacer(width=125)

                    checkboxLeftShakeEffect = dpg.add_checkbox(label="Shake Effect", default_value=sharpClass.config["left"]["shakeEffect"], callback=toggleLeftShakeEffect)
                    sliderLeftShakeEffectForce = dpg.add_slider_int(label="Shake Effect Force", default_value=sharpClass.config["left"]["shakeEffectForce"], min_value=1, max_value=20, callback=setLeftShakeEffectForce)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    inputLeftClickSoundPath = dpg.add_input_text(label="Click Sound Path (empty for no sound)", default_value=sharpClass.config["left"]["soundPath"], hint="Exemple: mysounds/G505.wav", callback=setLeftClickSoundPath)

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

                    inputRightClickSoundPath = dpg.add_input_text(label="Click Sound Path (empty for no sound)", default_value=sharpClass.config["right"]["soundPath"], hint="Exemple: mysounds/G505.wav", callback=setRightClickSoundPath)

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxRightWorkInMenus = dpg.add_checkbox(label="Work in Menus", default_value=sharpClass.config["right"]["workInMenus"], callback=toggleRightWorkInMenus)
                    checkboxRightBlatantMode = dpg.add_checkbox(label="Blatant Mode", default_value=sharpClass.config["right"]["blatant"], callback=toggleRightBlatantMode)

                with dpg.tab(label="Aim Assist"):
                    dpg.add_spacer(width=75)

                    with dpg.group(horizontal=True):
                        checkboxToggleAimAssist = dpg.add_checkbox(label="Toggle", default_value=sharpClass.config["aimassist"]["enabled"], callback=toggleAimAssist)
                        buttonBindAimAssist = dpg.add_button(label="Click to Bind", callback=statusBindAimAssist)

                        bind = sharpClass.config["aimassist"]["bind"]
                        if bind != 0:
                            dpg.set_item_label(buttonBindAimAssist, f"Bind: {chr(bind)}")

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    dpg.add_text("Target Settings: Helps you keep your aim on target by smoothly adjusting your crosshair's position.")

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxClickAim = dpg.add_checkbox(label="Click Aim", default_value=sharpClass.config["aimassist"]["clickAim"], callback=toggleClickAim)
                    dpg.add_text("Restrict's AimAssist's functionality so that it only functions while you are clicking.")

                    dpg.add_spacer(width=75)

                    checkboxStrafeIncrease = dpg.add_checkbox(label="Strafe Increase", default_value=sharpClass.config["aimassist"]["strafeIncrease"], callback=toggleStrafeIncrease)
                    dpg.add_text("Increases the speed of crosshair adjustment when you or your opponent are strafing.")

                    dpg.add_spacer(width=75)

                    checkboxCheckBlockBreak = dpg.add_checkbox(label="Check Block Break", default_value=sharpClass.config["aimassist"]["checkBlockBreak"], callback=toggleCheckBlockBreak)
                    dpg.add_text("Pauses the module while breaking blocks.")
                    inputBlockBreakWhitelist = dpg.add_input_text(label="Break Blocks Whitelist", default_value=sharpClass.config["aimassist"]["blockBreakWhitelist"], callback=setBlockBreakWhitelist)
                    dpg.add_text("Specify a list of items that will be able to break blocks with AimAssist and Check Block Break enabled.")

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxAimVertically = dpg.add_checkbox(label="Aim Vertically", default_value=sharpClass.config["aimassist"]["aimVertically"], callback=toggleAimVertically)
                    sliderVerticalSpeed = dpg.add_slider_int(label="Vertical Speed", default_value=sharpClass.config["aimassist"]["verticalSpeed"], min_value=1, max_value=10, callback=setVerticalSpeed)
                    dpg.add_text("Controls the speed of vertical aim adjustment.")

                    sliderHorizontalSpeed = dpg.add_slider_int(label="Horizontal Speed", default_value=sharpClass.config["aimassist"]["horizontalSpeed"], min_value=1, max_value=10, callback=setHorizontalSpeed)
                    dpg.add_text("Controls the speed of horizontal aim adjustment.")

                    dpg.add_spacer(width=75)

                    sliderMaxAngle = dpg.add_slider_int(label="Max Angle", default_value=sharpClass.config["aimassist"]["maxAngle"], min_value=1, max_value=90, callback=setMaxAngle)
                    dpg.add_text("Specifies the maximum angle from your crosshair position that a target can be, for that target to be considered a valid target.")

                    sliderDistance = dpg.add_slider_int(label="Distance", default_value=sharpClass.config["aimassist"]["distance"], min_value=1, max_value=100, callback=setDistance)
                    dpg.add_text("The maximum distance for an entity to be considered a target.")

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    checkboxLimitToItems = dpg.add_checkbox(label="Limit to Items", default_value=sharpClass.config["aimassist"]["limitToItems"], callback=toggleLimitToItems)
                    inputItemsWhitelist = dpg.add_input_text(label="Items Whitelist", default_value=sharpClass.config["aimassist"]["itemsWhitelist"], callback=setItemsWhitelist)
                    dpg.add_text("Restricts AimAssist's functionality so that it only functions while specified items are held in your hand.")

                    dpg.add_spacer(width=75)

                    comboTargetArea = dpg.add_combo(label="Target Area", items=["Center", "Closest"], default_value=sharpClass.config["aimassist"]["targetArea"], callback=setTargetArea)
                    dpg.add_text("Specifies which part of the target's hitbox the module will aim towards.")

                    comboTargetMode = dpg.add_combo(label="Target Mode", items=["Distance", "Yaw", "Armor", "Threat", "Health"], default_value=sharpClass.config["aimassist"]["targetMode"], callback=setTargetMode)
                    dpg.add_text("Determines how a module prioritizes target selection when multiple targets are available.")

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

                    dpg.add_spacer(width=75)
                    dpg.add_separator()
                    dpg.add_spacer(width=75)

                    creditsText = dpg.add_text(default_value="Credits: Bambou (Developer) - Enhanced by Sharp+")
                    githubText = dpg.add_text(default_value="https://github.com/B4mb0u/Sharp")

        # Apply initial theme
        updateTheme()

        dpg.show_viewport()

        guiWindows = win32gui.GetForegroundWindow()

        dpg.setup_dearpygui()
        dpg.set_primary_window("Primary Window", True)
        dpg.start_dearpygui()

        selfDestruct()
    except KeyboardInterrupt:

        os._exit(0)

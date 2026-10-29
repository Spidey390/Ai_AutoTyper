import re

with open("Ai_AutoTyper_Windows/main.py", "r") as f:
    content = f.read()

# 1. Platform imports
imports_old = """try:
    import pyautogui
    import keyboard
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pyautogui", "keyboard", "customtkinter", "mss", "pillow", "google-generativeai", "--break-system-packages"],
                   capture_output=True)
    import pyautogui
    import keyboard"""

imports_new = """IS_MAC = sys.platform == "darwin"
try:
    import pyautogui
    if not IS_MAC:
        import keyboard
except ImportError:
    import subprocess
    pkgs = ["pyautogui", "customtkinter", "mss", "pillow", "google-generativeai"]
    if not IS_MAC: pkgs.append("keyboard")
    else: pkgs.append("pynput")
    subprocess.run([sys.executable, "-m", "pip", "install"] + pkgs + ["--break-system-packages"], capture_output=True)
    import pyautogui
    if not IS_MAC:
        import keyboard

if IS_MAC:
    try:
        import Quartz
    except ImportError:
        pass"""

content = content.replace(imports_old, imports_new)

# 2. Type code engine modification
type_code_old = """        if ch == '\\n':
            pyautogui.press('enter')
        elif ch == '\\t':
            pyautogui.press('tab')
        else:
            pyautogui.write(ch, interval=0)"""
type_code_new = """        if IS_MAC and 'Quartz' in globals():
            src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
            if ch == '\\n':
                for down in (True, False):
                    e = Quartz.CGEventCreateKeyboardEvent(src, 36, down)
                    Quartz.CGEventPost(Quartz.kCGSessionEventTap, e)
            elif ch == '\\t':
                for down in (True, False):
                    e = Quartz.CGEventCreateKeyboardEvent(src, 48, down)
                    Quartz.CGEventPost(Quartz.kCGSessionEventTap, e)
            else:
                for down in (True, False):
                    e = Quartz.CGEventCreateKeyboardEvent(src, 0, down)
                    Quartz.CGEventKeyboardSetUnicodeString(e, len(ch), ch)
                    Quartz.CGEventPost(Quartz.kCGSessionEventTap, e)
        else:
            if ch == '\\n':
                pyautogui.press('enter')
            elif ch == '\\t':
                pyautogui.press('tab')
            else:
                pyautogui.write(ch, interval=0)"""
content = content.replace(type_code_old, type_code_new)

# 3. Hotkeys modification
hotkeys_old = """# ── Global hotkeys ──
keyboard.add_hotkey("ctrl+q", lambda: app.after(0, on_ctrl_q), suppress=True)

# Register the Gemini hotkey based on config (defaults to your preference, e.g., ctrl+shift+q)
config_data = load_config()
gemini_hotkey = config_data.get("hotkey", "ctrl+shift+q")
keyboard.add_hotkey(gemini_hotkey, lambda: app.after(0, run_gemini_pipeline), suppress=True)

# Register Error Fix hotkey
keyboard.add_hotkey("ctrl+shift+e", lambda: app.after(0, run_gemini_error_pipeline), suppress=True)"""

hotkeys_new = """# ── Global hotkeys ──
if not IS_MAC:
    keyboard.add_hotkey("ctrl+q", lambda: app.after(0, on_ctrl_q), suppress=True)
    config_data = load_config()
    gemini_hotkey = config_data.get("hotkey", "ctrl+shift+q")
    keyboard.add_hotkey(gemini_hotkey, lambda: app.after(0, run_gemini_pipeline), suppress=True)
    keyboard.add_hotkey("ctrl+shift+e", lambda: app.after(0, run_gemini_error_pipeline), suppress=True)
else:
    app._hotkey_pressed = False
    app._ai_hotkey_pressed = False
    app._ai_error_hotkey_pressed = False
    
    def poll_hotkey():
        try:
            ctrl = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 59)
            ctrl2 = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 62)
            cmd = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 55)
            cmd2 = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 54)
            shift = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 56)
            shift2 = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 60)
            q = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 12)
            e_key = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 14)
            
            is_mod = (ctrl or ctrl2 or cmd or cmd2)
            is_shift = (shift or shift2)
            
            if is_mod and is_shift and q:
                if not app._ai_hotkey_pressed:
                    app._ai_hotkey_pressed = True
                    run_gemini_pipeline()
            elif is_mod and is_shift and e_key:
                if not app._ai_error_hotkey_pressed:
                    app._ai_error_hotkey_pressed = True
                    run_gemini_error_pipeline()
            elif is_mod and not is_shift and q:
                if not app._hotkey_pressed and not app._ai_hotkey_pressed:
                    app._hotkey_pressed = True
                    app.after(150, lambda: on_ctrl_q() if (not app._ai_hotkey_pressed and app._hotkey_pressed) else None)
            else:
                if not (is_mod or q or e_key):
                    app._hotkey_pressed = False
                    app._ai_hotkey_pressed = False
                    app._ai_error_hotkey_pressed = False
        except Exception:
            pass
        app.after(50, poll_hotkey)
    
    if 'Quartz' in globals():
        app.after(50, poll_hotkey)"""

content = content.replace(hotkeys_old, hotkeys_new)

with open("Ai_AutoTyper_Windows/main.py", "w") as f:
    f.write(content)

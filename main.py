import json
import os
import sys
import threading
import time
import random
import re
from pathlib import Path

import customtkinter as ctk

try:
    import pyautogui
    import pyperclip
    from pynput import keyboard
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pyautogui", "pyperclip", "pynput", "customtkinter", "mss", "pillow", "google-genai", "--break-system-packages"],
                   capture_output=True)
    import pyautogui
    import pyperclip
    from pynput import keyboard

from PIL import Image
from screenshot import capture_screen_image
from gemini_client import get_solution, get_fixed_solution

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print("[ERROR] config.json not found! Please create it with your API key.")
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(config_dict: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_dict, f, indent=4)

# ── PyAutoGUI Settings ──
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0  # CRITICAL: Removes pyautogui's default 0.1s pause which severely limits max typing speed

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BG_COLOR    = "#0B0F19"
PANEL_COLOR = "#151B2B"
ACCENT      = "#3B82F6"
SUCCESS     = "#10B981"
DANGER      = "#EF4444"
WARNING     = "#F59E0B"
TEXT_MUTED  = "#9CA3AF"

typing_active = False
typing_thread = None
processing_gemini = False
last_generated_code = ""
HOTKEY_DISAMBIGUATION_MS = 150

# ── Animated Toast ──
class AnimatedToast(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=PANEL_COLOR, corner_radius=8,
                         border_width=1, border_color="#2D3748", **kwargs)
        self.label = ctk.CTkLabel(self, text="", font=("Segoe UI", 13, "bold"))
        self.label.pack(padx=20, pady=10)
        self.current_y = -0.1
        self.target_y  = -0.1
        self.animating = False

    def show(self, message, color_hex):
        self.label.configure(text=message, text_color=color_hex)
        self.target_y = 0.05
        self.place(relx=0.5, rely=self.current_y, anchor="center")
        self.lift()
        if not self.animating:
            self._animate()

    def hide(self):
        self.target_y = -0.1
        if not self.animating:
            self._animate()

    def _animate(self):
        self.animating = True
        diff = self.target_y - self.current_y
        self.current_y += diff * 0.15
        self.place(relx=0.5, rely=self.current_y, anchor="center")
        if abs(diff) > 0.001:
            self.after(16, self._animate)
        else:
            self.animating = False

# ── Typing engine ──
def human_delay(wpm):
    # 1 Word = 5 chars => Delay per char in sec = 12 / WPM
    base_delay = 12.0 / max(1, wpm)
    # Add human-like random jitter
    jitter  = random.gauss(0, base_delay * 0.15)
    return max(0.001, base_delay + jitter)

SHIFTED_CHARS = {
    '~': '`', '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0', '_': '-',
    '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'",
    '<': ',', '>': '.', '?': '/'
}

def safe_type(ch):
    if ch.isupper():
        pyautogui.keyDown('shift')
        time.sleep(0.005)
        pyautogui.keyDown(ch.lower())
        time.sleep(0.005)
        pyautogui.keyUp(ch.lower())
        time.sleep(0.005)
        pyautogui.keyUp('shift')
    elif ch in SHIFTED_CHARS:
        pyautogui.keyDown('shift')
        time.sleep(0.005)
        pyautogui.keyDown(SHIFTED_CHARS[ch])
        time.sleep(0.005)
        pyautogui.keyUp(SHIFTED_CHARS[ch])
        time.sleep(0.005)
        pyautogui.keyUp('shift')
    else:
        if ord(ch) < 128:
            pyautogui.write(ch, interval=0)
        else:
            try:
                cb = pyperclip.paste()
                pyperclip.copy(ch)
                pyautogui.hotkey("command" if sys.platform == "darwin" else "ctrl", "v")
                time.sleep(0.06)
                pyperclip.copy(cb)
            except:
                pyautogui.write(ch, interval=0)

def type_code(text, target_wpm):
    global typing_active
    time.sleep(3)
    
    try:
        for ch in text:
            if not typing_active:
                break
            delay = human_delay(target_wpm)

            if ch == '\n':
                pyautogui.press('enter')
            elif ch == '\t':
                pyautogui.press('tab')
            else:
                safe_type(ch)
            time.sleep(delay)
    except Exception as e:
        print(f"Typing error: {e}")
    finally:
        typing_active = False
        app.after(0, lambda: update_ui_state("✅ Done typing!", SUCCESS, False))

# ── Hotkey handlers ──
def on_ctrl_q():
    global typing_active, typing_thread
    # Ctrl+Q is a subset of the default Gemini shortcut Ctrl+Shift+Q on some
    # platforms.  Do not let the typing action start while a Gemini request is
    # being launched for that same key press.
    if processing_gemini:
        return
    if typing_active:
        typing_active = False
        app.after(0, lambda: update_ui_state("⛔ Stopped.", WARNING, False))
    else:
        code = code_box.get("1.0", ctk.END).rstrip('\n')
        if placeholder_active or not code.strip():
            app.after(0, lambda: toast.show("⚠️ No code to type!", DANGER))
            app.after(3000, toast.hide)
            return
        typing_wpm = speed_var.get()
        typing_active = True
        app.after(0, lambda: update_ui_state("⌨️ Starting in 3s... Get ready!", ACCENT, True))
        typing_thread = threading.Thread(
            target=type_code,
            args=(code, typing_wpm),
            daemon=True
        )
        typing_thread.start()

# ── GUI helpers ──
def update_ui_state(msg, color, running):
    toast.show(msg, color)
    if not running:
        app.after(4000, toast.hide)
    start_btn.configure(state="disabled" if running else "normal",
                        fg_color=PANEL_COLOR if running else ACCENT)
    stop_btn.configure(state="normal" if running else "disabled",
                       fg_color=DANGER if running else PANEL_COLOR)

# ── Build GUI ──
app = ctk.CTk()
app.title("AutoTyper Pro + Gemini")
app.geometry("1000x520")
app.configure(fg_color=BG_COLOR)
app.resizable(False, False)  # disables maximize button

app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

toast = AnimatedToast(app)

# ── Sidebar ──
sidebar = ctk.CTkFrame(app, width=280, corner_radius=0, fg_color=PANEL_COLOR)
sidebar.grid(row=0, column=0, sticky="nsew")
sidebar.grid_rowconfigure(8, weight=1)

ctk.CTkLabel(sidebar, text="⚡ AutoTyper Pro",
             font=("Segoe UI", 20, "bold"), text_color="white").grid(
    row=0, column=0, padx=20, pady=(30, 5), sticky="w")
ctk.CTkLabel(sidebar, text="Gemini-Integrated Code Injection",
             font=("Segoe UI", 12), text_color=TEXT_MUTED).grid(
    row=1, column=0, padx=20, pady=(0, 30), sticky="w")

settings_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
settings_frame.grid(row=2, column=0, padx=20, sticky="ew")

speed_var = ctk.DoubleVar(value=200)  # ← 200 WPM

def create_slider(parent, label_text, var, from_, to):
    ctk.CTkLabel(parent, text=label_text, font=("Segoe UI", 12),
                 text_color=TEXT_MUTED).pack(anchor="w")
    val_lbl = ctk.CTkLabel(parent, text=f"{int(var.get())} WPM",
                           font=("Segoe UI", 12, "bold"), text_color="white")
    def on_change(v):
        val_lbl.configure(text=f"{int(v)} WPM")
    ctk.CTkSlider(parent, from_=from_, to=to, variable=var, command=on_change,
                  button_color=ACCENT, progress_color=ACCENT).pack(fill="x", pady=(5, 0))
    val_lbl.pack(anchor="e", pady=(0, 15))

create_slider(settings_frame, "Typing Speed (WPM)", speed_var, 10, 500)

start_btn = ctk.CTkButton(sidebar, text="▶ Start (Ctrl+Q)", command=on_ctrl_q,
                          font=("Segoe UI", 14, "bold"), fg_color=ACCENT,
                          hover_color="#2563EB", height=45)
start_btn.grid(row=4, column=0, padx=20, pady=(20, 10), sticky="ew")

stop_btn = ctk.CTkButton(sidebar, text="⏹ Stop",
                         command=lambda: on_ctrl_q() if typing_active else None,
                         font=("Segoe UI", 14, "bold"), fg_color=PANEL_COLOR,
                         hover_color="#B91C1C", height=45, state="disabled")
stop_btn.grid(row=5, column=0, padx=20, pady=0, sticky="ew")

fix_error_btn = ctk.CTkButton(
    sidebar, text="🛠 Fix Error (Ctrl+Shift+E)",
    command=lambda: run_gemini_error_pipeline(),
    font=("Segoe UI", 14, "bold"), fg_color="#7C3AED",
    hover_color="#6D28D9", height=45
)
fix_error_btn.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="ew")

def open_settings():
    settings_win = ctk.CTkToplevel(app)
    settings_win.title("Settings")
    settings_win.geometry("400x380")
    settings_win.attributes("-topmost", True)
    
    current_config = load_config()
    
    ctk.CTkLabel(settings_win, text="Gemini API Key:", font=("Segoe UI", 14)).pack(pady=(20, 5), padx=20, anchor="w")
    api_entry = ctk.CTkEntry(settings_win, width=360, show="*")
    api_entry.pack(pady=5, padx=20)
    api_entry.insert(0, current_config.get("api_key", ""))
    
    ctk.CTkLabel(settings_win, text="Model:", font=("Segoe UI", 14)).pack(pady=(10, 5), padx=20, anchor="w")
    model_var = ctk.StringVar(value=current_config.get("model", "gemini-flash-latest"))
    model_dropdown = ctk.CTkOptionMenu(settings_win, variable=model_var, width=360,
                                       values=["gemini-flash-latest", "gemini-pro-latest", "gemini-3.5-flash", "gemini-2.0-flash"])
    model_dropdown.pack(pady=5, padx=20)
    
    ctk.CTkLabel(settings_win, text="Gemini Trigger Hotkey:", font=("Segoe UI", 14)).pack(pady=(10, 5), padx=20, anchor="w")
    hotkey_entry = ctk.CTkEntry(settings_win, width=360)
    hotkey_entry.pack(pady=5, padx=20)
    hotkey_entry.insert(0, current_config.get("hotkey", "ctrl+shift+q"))
    
    def save_and_close():
        current_config["api_key"] = api_entry.get().strip()
        current_config["model"] = model_var.get().strip()
        current_config["hotkey"] = hotkey_entry.get().strip()
        save_config(current_config)
        settings_win.destroy()
        toast.show("✅ Saved! Restart app if hotkey changed.", SUCCESS)
        app.after(4000, toast.hide)
        
    ctk.CTkButton(settings_win, text="Save", command=save_and_close, fg_color=ACCENT, hover_color="#2563EB").pack(pady=20)

settings_btn = ctk.CTkButton(sidebar, text="⚙️ Settings", command=open_settings,
                             font=("Segoe UI", 14, "bold"), fg_color="#1E293B",
                             hover_color="#334155", height=45)
settings_btn.grid(row=7, column=0, padx=20, pady=(10, 20), sticky="ew")

def remove_indentation():
    text = code_box.get("1.0", ctk.END)
    # Strip ALL leading whitespace from every single line
    lines = [line.lstrip() for line in text.splitlines()]
    # Remove leading blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    cleaned = "\n".join(lines)
    code_box.delete("1.0", ctk.END)
    code_box.insert("1.0", cleaned)
    toast.show("✅ Indentation removed!", SUCCESS)
    app.after(3000, toast.hide)


# ── Main content ──
main_content = ctk.CTkFrame(app, fg_color="transparent")
main_content.grid(row=0, column=1, padx=30, pady=30, sticky="nsew")
main_content.grid_rowconfigure(1, weight=1)
main_content.grid_columnconfigure(0, weight=1)

header = ctk.CTkFrame(main_content, fg_color="transparent")
header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
ctk.CTkLabel(header, text="Payload Editor",
             font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")
def paste_code():
    try:
        clipboard = app.clipboard_get()
    except Exception:
        toast.show("⚠️ Clipboard is empty!", DANGER)
        app.after(3000, toast.hide)
        return
    _placeholder_clear()
    code_box.delete("1.0", ctk.END)
    code_box.insert("1.0", clipboard)
    toast.show("📋 Pasted!", SUCCESS)
    app.after(2000, toast.hide)

dedent_btn = ctk.CTkButton(header, text="⇤ Remove Indentation", command=remove_indentation,
                           font=("Segoe UI", 12, "bold"), fg_color="#1E293B",
                           hover_color="#334155", text_color=TEXT_MUTED, height=35,
                           border_width=1, border_color="#2D3748")
dedent_btn.pack(side="right", padx=(6, 0))

paste_btn = ctk.CTkButton(header, text="📋 Paste", command=paste_code,
                          font=("Segoe UI", 12, "bold"), fg_color=ACCENT,
                          hover_color="#2563EB", text_color="white", height=35)
paste_btn.pack(side="right")

PLACEHOLDER        = "// Paste your code payload here\n// Or press your configured hotkey to Auto-Solve!"
PLACEHOLDER_COLOR  = "#4B5563"   # muted grey
CODE_COLOR         = "#A5B4FC"   # normal code colour
placeholder_active = True

code_box = ctk.CTkTextbox(main_content, font=("Consolas", 15), fg_color=PANEL_COLOR,
                          text_color=PLACEHOLDER_COLOR, border_color="#2D3748",
                          border_width=1, corner_radius=12)
code_box.grid(row=1, column=0, sticky="nsew")
code_box.insert("1.0", PLACEHOLDER)

def _placeholder_clear(event=None):
    global placeholder_active
    if placeholder_active:
        placeholder_active = False
        code_box.delete("1.0", ctk.END)
        code_box.configure(text_color=CODE_COLOR)

def _placeholder_restore(event=None):
    global placeholder_active
    if not placeholder_active and not code_box.get("1.0", ctk.END).strip():
        placeholder_active = True
        code_box.delete("1.0", ctk.END)
        code_box.insert("1.0", PLACEHOLDER)
        code_box.configure(text_color=PLACEHOLDER_COLOR)

code_box._textbox.bind("<FocusIn>",  _placeholder_clear)
code_box._textbox.bind("<FocusOut>", _placeholder_restore)

# ── GEMINI INTEGRATION & AUTOMATION PIPELINE ──
def clean_markdown_code(text):
    """Extract code from markdown blocks, ignoring any conversational text or CoT reasoning."""
    # Find all blocks wrapped in ```, capturing the language tag
    blocks = re.findall(r"```([^\n]*)\n(.*?)```", text, re.DOTALL)
    if blocks:
        # Return the longest code block and its language
        longest_block = max(blocks, key=lambda b: len(b[1]))
        lang = longest_block[0].lower().strip()
        code = longest_block[1].strip()
        return code, lang
    
    # Fallback if it didn't use markdown blocks
    return text.strip(), ""

def run_gemini_pipeline():
    global processing_gemini
    if processing_gemini or typing_active:
        app.after(0, lambda: toast.show("⚠️ Already processing or typing!", WARNING))
        return
    processing_gemini = True
    app.after(0, lambda: toast.show("📸 Capturing screenshot...", ACCENT))
    
    def clear_editor_for_loading():
        _placeholder_clear()
        code_box.delete("1.0", ctk.END)
        code_box.insert("1.0", "⏳ Waiting for Gemini to generate solution...\n(This usually takes 2-5 seconds)")
        code_box.configure(text_color=TEXT_MUTED)
    app.after(0, clear_editor_for_loading)

    def task():
        global processing_gemini
        try:
            # 1. Capture screen
            full_img, thumbnail_img = capture_screen_image()

            config_data = load_config()
            api_key = config_data.get("api_key", "")
            model = config_data.get("model", "gemini-flash-latest")

            if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
                raise ValueError("API Key missing in config.json")

            # 2. Query Gemini
            def progress(msg):
                app.after(0, lambda: toast.show(f"🤖 {msg}", ACCENT))

            solution = get_solution(api_key, model, full_img, progress_callback=progress)
            cleaned_code, lang = clean_markdown_code(solution)

            global last_generated_code
            last_generated_code = cleaned_code

            # 3. Inject, dedent, and trigger typing via UI thread
            app.after(0, lambda: execute_gemini_result(cleaned_code, lang))

        except Exception as e:
            err_msg = str(e)
            app.after(0, lambda msg=err_msg: toast.show(f"❌ Error: {msg}", DANGER))
            processing_gemini = False
            
            def restore_on_error():
                code_box.delete("1.0", ctk.END)
                _placeholder_restore()
            app.after(0, restore_on_error)

    threading.Thread(target=task, daemon=True).start()

def execute_gemini_result(code, lang=""):
    global processing_gemini
    try:
        # Step A: Paste code into the editor
        _placeholder_clear()
        code_box.delete("1.0", ctk.END)
        code_box.insert("1.0", code)
        code_box.configure(text_color=CODE_COLOR)
        
        # Step B: Remove indentation for everything EXCEPT Python
        if lang not in ["python", "py", "python3"]:
            remove_indentation()
        
        # Step C: Delay briefly to let the user focus and UI update, then trigger typing natively
        app.after(800, on_ctrl_q)
    finally:
        processing_gemini = False

def run_gemini_error_pipeline():
    global processing_gemini, last_generated_code
    if processing_gemini or typing_active:
        app.after(0, lambda: toast.show("⚠️ Already processing or typing!", WARNING))
        return
    if not last_generated_code.strip():
        app.after(0, lambda: toast.show("⚠️ No previous code to fix!", DANGER))
        return
        
    processing_gemini = True
    app.after(0, lambda: toast.show("📸 Capturing error screenshot...", ACCENT))

    def clear_editor_for_loading():
        _placeholder_clear()
        code_box.delete("1.0", ctk.END)
        code_box.insert("1.0", "⏳ Waiting for Gemini to analyze and fix the error...\n(This usually takes 2-5 seconds)")
        code_box.configure(text_color=TEXT_MUTED)
    app.after(0, clear_editor_for_loading)

    def task():
        global processing_gemini, last_generated_code
        try:
            full_img, thumbnail_img = capture_screen_image()

            config_data = load_config()
            api_key = config_data.get("api_key", "")
            model = config_data.get("model", "gemini-flash-latest")

            if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
                raise ValueError("API Key missing in config.json")

            def progress(msg):
                app.after(0, lambda: toast.show(f"🤖 {msg}", ACCENT))

            solution = get_fixed_solution(api_key, model, full_img, last_generated_code, progress_callback=progress)
            cleaned_code, lang = clean_markdown_code(solution)
            
            last_generated_code = cleaned_code

            app.after(0, lambda: execute_gemini_result(cleaned_code, lang))

        except Exception as e:
            err_msg = str(e)
            app.after(0, lambda msg=err_msg: toast.show(f"❌ Error: {msg}", DANGER))
            processing_gemini = False
            
            def restore_on_error():
                code_box.delete("1.0", ctk.END)
                _placeholder_restore()
            app.after(0, restore_on_error)

    threading.Thread(target=task, daemon=True).start()


# ── Global hotkeys ──
def dispatch_typing_hotkey():
    """Delay Ctrl+Q briefly so a longer Gemini chord can take precedence."""
    app.after(HOTKEY_DISAMBIGUATION_MS, on_ctrl_q)


def parse_hotkey(hk):
    parts = hk.split('+')
    pynput_parts = []
    for p in parts:
        p = p.strip().lower()
        if p in ['ctrl', 'shift', 'alt', 'cmd', 'command', 'option']:
            if p in ['cmd', 'command']: p = 'cmd'
            if p in ['alt', 'option']: p = 'alt'
            pynput_parts.append(f"<{p}>")
        else:
            pynput_parts.append(p)
    return "+".join(pynput_parts)

config_data = load_config()
gemini_hotkey = config_data.get("hotkey", "")
if not gemini_hotkey.strip():
    gemini_hotkey = "ctrl+shift+q"

hotkeys = {}
try:
    hotkeys[parse_hotkey("ctrl+q")] = dispatch_typing_hotkey
    hotkeys[parse_hotkey(gemini_hotkey)] = lambda: app.after(0, run_gemini_pipeline)
    hotkeys[parse_hotkey("ctrl+shift+e")] = lambda: app.after(0, run_gemini_error_pipeline)
except ValueError as e:
    print(f"Warning: Invalid hotkey format! {e}")

listener = keyboard.GlobalHotKeys(hotkeys)
listener.start()

if __name__ == "__main__":
    app.mainloop()

import json
import sys
import threading
import time
import random
import subprocess
import ctypes
from pathlib import Path
import screenshot
import gemini_client

CONFIG_PATH = Path("config.json")
def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_key": "", "model": "gemini-2.5-pro"}

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

app_config = load_config()

# Reacquire GIL when called from C-level callbacks (CFRunLoop fires while
# tkinter's mainloop has released the GIL, leaving thread state NULL in Py 3.13)
_lib = ctypes.PyDLL(None)
_lib.PyGILState_Ensure.restype = ctypes.c_int
_lib.PyGILState_Release.argtypes = [ctypes.c_int]

try:
    import customtkinter as ctk
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "customtkinter"], capture_output=True)
    import customtkinter as ctk

try:
    from pynput import keyboard as pynput_keyboard
    _HAS_PYNPUT = True
except ImportError:
    _HAS_PYNPUT = False

# macOS-native backends (thread-safe, no TSM calls)
try:
    import Quartz
    from AppKit import NSEvent
    _USE_MACOS_NATIVE = True
except ImportError:
    _USE_MACOS_NATIVE = False

# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BG_COLOR    = "#0B0F19"
PANEL_COLOR = "#151B2B"
ACCENT      = "#3B82F6"
SUCCESS     = "#10B981"
DANGER      = "#EF4444"
WARNING     = "#F59E0B"
TEXT_MUTED  = "#9CA3AF"

IS_MAC    = sys.platform == "darwin"
FONT_UI   = "Helvetica Neue" if IS_MAC else "Segoe UI"
FONT_CODE = "Menlo"          if IS_MAC else "Consolas"

# ── State ─────────────────────────────────────────────────────────────────────
typing_active = False
typing_thread = None
_last_start_trigger = 0.0
_last_ai_trigger    = 0.0
last_generated_code = ""

# pynput Controller only used on non-macOS (TSM-safe)
_kb_controller = None
if not (IS_MAC and _USE_MACOS_NATIVE) and _HAS_PYNPUT:
    _kb_controller = pynput_keyboard.Controller()

# ── Animated Toast ────────────────────────────────────────────────────────────
class AnimatedToast(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=PANEL_COLOR, corner_radius=8,
                         border_width=1, border_color="#2D3748", **kwargs)
        self.label = ctk.CTkLabel(self, text="", font=(FONT_UI, 13, "bold"))
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

# ── Typing engine ─────────────────────────────────────────────────────────────
_RETURN_KEYCODE = 36
_TAB_KEYCODE    = 48

def _post_quartz_char(char: str):
    """Type one character via CGEvent (thread-safe, no TSM dependency)."""
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    if char == "\n":
        for down in (True, False):
            e = Quartz.CGEventCreateKeyboardEvent(src, _RETURN_KEYCODE, down)
            Quartz.CGEventPost(Quartz.kCGSessionEventTap, e)
    elif char == "\t":
        for down in (True, False):
            e = Quartz.CGEventCreateKeyboardEvent(src, _TAB_KEYCODE, down)
            Quartz.CGEventPost(Quartz.kCGSessionEventTap, e)
    else:
        for down in (True, False):
            e = Quartz.CGEventCreateKeyboardEvent(src, 0, down)
            Quartz.CGEventKeyboardSetUnicodeString(e, len(char), char)
            Quartz.CGEventPost(Quartz.kCGSessionEventTap, e)


def _post_pynput_char(char: str):
    """Type one character via pynput Controller (non-macOS fallback)."""
    if char == "\n":
        _kb_controller.press(pynput_keyboard.Key.enter)
        _kb_controller.release(pynput_keyboard.Key.enter)
    elif char == "\t":
        _kb_controller.press(pynput_keyboard.Key.tab)
        _kb_controller.release(pynput_keyboard.Key.tab)
    else:
        _kb_controller.type(char)


def human_delay(wpm: float) -> float:
    base   = 12.0 / max(1, wpm)
    jitter = random.gauss(0, base * 0.15)
    return max(0.001, base + jitter)


def type_code(text: str, target_wpm: float):
    global typing_active
    time.sleep(3)

    _post_char = _post_quartz_char if (IS_MAC and _USE_MACOS_NATIVE) else _post_pynput_char

    for ch in text:
        if not typing_active:
            break
        try:
            _post_char(ch)
        except Exception:
            pass
        time.sleep(human_delay(target_wpm))

    typing_active = False
    app.after(0, lambda: update_ui_state("Done typing!", SUCCESS, False))

# ── Hotkey handler ────────────────────────────────────────────────────────────
def on_start_stop():
    global typing_active, typing_thread, _last_start_trigger
    now = time.time()
    if now - _last_start_trigger < 1.0:
        return
    _last_start_trigger = now
    if typing_active:
        typing_active = False
        app.after(0, lambda: update_ui_state("Stopped.", WARNING, False))
    else:
        code = code_box.get("1.0", ctk.END).rstrip("\n")
        if placeholder_active or not code.strip():
            app.after(0, lambda: toast.show("No text to type!", DANGER))
            app.after(3000, toast.hide)
            return
        typing_active = True
        app.after(0, lambda: update_ui_state("Starting in 3s… Switch to target window!", ACCENT, True))
        typing_thread = threading.Thread(
            target=type_code, args=(code, speed_var.get()), daemon=True
        )
        typing_thread.start()


def clean_markdown_code(text):
    import re
    code = text.strip()
    if code.startswith("```"):
        code = re.sub(r"^```[a-zA-Z]*\n", "", code)
        code = re.sub(r"\n```$", "", code)
    return code.strip()

def ai_auto_type_worker():
    global typing_active
    api_key = app_config.get("api_key", "").strip()
    if not api_key:
        app.after(0, lambda: toast.show("Please set Gemini API Key in Settings!", DANGER))
        app.after(3000, toast.hide)
        typing_active = False
        app.after(0, lambda: update_ui_state("Failed.", WARNING, False))
        return
        
    try:
        app.after(0, lambda: update_ui_state("Capturing screen...", ACCENT, True))
        img, _ = screenshot.capture_screen_image()
        
        def progress(msg):
            app.after(0, lambda: toast.show(msg, ACCENT))
            
        model = app_config.get("model", "gemini-2.5-pro")
        code = gemini_client.get_solution(api_key, model, img, progress)
        code = clean_markdown_code(code)
        global last_generated_code
        last_generated_code = code
        
        # Remove indentation
        lines = [line.lstrip() for line in code.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        code = "\n".join(lines)
        
        if not code.strip():
            raise RuntimeError("Gemini returned no executable code.")
            
        app.after(0, _placeholder_clear)
        app.after(0, lambda: code_box.delete("1.0", ctk.END))
        app.after(0, lambda: code_box.insert("1.0", code))
        
        app.after(0, lambda: update_ui_state("Starting in 2s… Switch to target window!", ACCENT, True))
        time.sleep(2)
        type_code(code, speed_var.get())
    except Exception as e:
        typing_active = False
        err_str = str(e)
        app.after(0, lambda err=err_str: toast.show(f"Error: {err}", DANGER))
        app.after(4000, toast.hide)
        app.after(0, lambda: update_ui_state("Stopped.", WARNING, False))


def ai_error_fix_worker():
    global typing_active, last_generated_code
    if not last_generated_code.strip():
        app.after(0, lambda: toast.show("No previous code to fix!", DANGER))
        app.after(3000, toast.hide)
        return
        
    api_key = app_config.get("api_key", "").strip()
    if not api_key:
        app.after(0, lambda: toast.show("Please set Gemini API Key in Settings!", DANGER))
        app.after(3000, toast.hide)
        typing_active = False
        app.after(0, lambda: update_ui_state("Failed.", WARNING, False))
        return

    try:
        app.after(0, lambda: update_ui_state("Capturing error screen...", ACCENT, True))
        img, _ = screenshot.capture_screen_image()
        
        def progress(msg):
            app.after(0, lambda: toast.show(msg, ACCENT))
            
        model = app_config.get("model", "gemini-2.5-pro")
        code = gemini_client.get_fixed_solution(api_key, model, img, last_generated_code, progress)
        code = clean_markdown_code(code)
        
        last_generated_code = code

        # Remove indentation
        lines = [line.lstrip() for line in code.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        code = "\n".join(lines)
        
        if not code.strip():
            raise RuntimeError("Gemini returned no executable code.")
            
        app.after(0, _placeholder_clear)
        app.after(0, lambda: code_box.delete("1.0", ctk.END))
        app.after(0, lambda: code_box.insert("1.0", code))
        
        app.after(0, lambda: update_ui_state("Starting in 2s… Switch to target window!", ACCENT, True))
        time.sleep(2)
        type_code(code, speed_var.get())
    except Exception as e:
        typing_active = False
        err_str = str(e)
        app.after(0, lambda err=err_str: toast.show(f"Error: {err}", DANGER))
        app.after(4000, toast.hide)
        app.after(0, lambda: update_ui_state("Stopped.", WARNING, False))

def on_ai_error_fix():
    global typing_active, typing_thread, _last_ai_trigger
    now = time.time()
    if now - _last_ai_trigger < 1.0:
        return
    _last_ai_trigger = now
    if typing_active:
        typing_active = False
        app.after(0, lambda: update_ui_state("Stopped.", WARNING, False))
    else:
        typing_active = True
        typing_thread = threading.Thread(target=ai_error_fix_worker, daemon=True)
        typing_thread.start()

def on_ai_auto_type():
    global typing_active, typing_thread, _last_ai_trigger
    now = time.time()
    if now - _last_ai_trigger < 1.0:
        return
    _last_ai_trigger = now
    if typing_active:
        typing_active = False
        app.after(0, lambda: update_ui_state("Stopped.", WARNING, False))
    else:
        typing_active = True
        typing_thread = threading.Thread(target=ai_auto_type_worker, daemon=True)
        typing_thread.start()

# ── GUI helpers ───────────────────────────────────────────────────────────────
def update_ui_state(msg, color, running):
    toast.show(msg, color)
    if not running:
        app.after(4000, toast.hide)
    start_btn.configure(
        state="disabled" if running else "normal",
        fg_color=PANEL_COLOR if running else ACCENT,
    )
    stop_btn.configure(
        state="normal" if running else "disabled",
        fg_color=DANGER if running else PANEL_COLOR,
    )

# ── Build GUI ─────────────────────────────────────────────────────────────────
app = ctk.CTk()
app.title("AutoTyper Pro + Gemini")
app.geometry("1000x520")
app.configure(fg_color=BG_COLOR)
app.resizable(False, False)

app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

toast = AnimatedToast(app)

# ── Sidebar ───────────────────────────────────────────────────────────────────
sidebar = ctk.CTkFrame(app, width=260, corner_radius=0, fg_color=PANEL_COLOR)
sidebar.grid(row=0, column=0, sticky="nsew")
sidebar.grid_rowconfigure(6, weight=1)

sidebar_header = ctk.CTkFrame(sidebar, fg_color="transparent")
sidebar_header.grid(row=0, column=0, padx=20, pady=(30, 4), sticky="ew")
sidebar_header.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(sidebar_header, text="⚡ AutoTyper Pro",
             font=(FONT_UI, 20, "bold"), text_color="white").grid(row=0, column=0, sticky="w")

settings_btn = ctk.CTkButton(sidebar_header, text="⚙️", width=30, height=30,
                             fg_color="transparent", hover_color="#2D3748", text_color="white", font=(FONT_UI, 18),
                             command=lambda: open_settings())
settings_btn.grid(row=0, column=1, sticky="e")

ctk.CTkLabel(sidebar, text="Gemini-Integrated Code Injection",
             font=(FONT_UI, 12), text_color=TEXT_MUTED).grid(
    row=1, column=0, padx=20, pady=(0, 30), sticky="w")

settings_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
settings_frame.grid(row=2, column=0, padx=20, sticky="ew")

speed_var = ctk.DoubleVar(value=200)

def create_slider(parent, label_text, var, from_, to):
    ctk.CTkLabel(parent, text=label_text, font=(FONT_UI, 12),
                 text_color=TEXT_MUTED).pack(anchor="w")
    val_lbl = ctk.CTkLabel(parent, text=f"{int(var.get())} WPM",
                           font=(FONT_UI, 12, "bold"), text_color="white")
    def on_change(v):
        val_lbl.configure(text=f"{int(v)} WPM")
    ctk.CTkSlider(parent, from_=from_, to=to, variable=var, command=on_change,
                  button_color=ACCENT, progress_color=ACCENT).pack(fill="x", pady=(5, 0))
    val_lbl.pack(anchor="e", pady=(0, 15))

create_slider(settings_frame, "Typing Speed (WPM)", speed_var, 10, 500)

def open_settings():
    settings_win = ctk.CTkToplevel(app)
    settings_win.title("Settings")
    settings_win.geometry("400x300")
    settings_win.configure(fg_color=BG_COLOR)
    settings_win.attributes("-topmost", True)
    
    ctk.CTkLabel(settings_win, text="Settings", font=(FONT_UI, 20, "bold"), text_color="white").pack(pady=(20, 10))
    
    ctk.CTkLabel(settings_win, text="Gemini API Key", font=(FONT_UI, 12), text_color=TEXT_MUTED).pack(anchor="w", padx=30)
    api_entry = ctk.CTkEntry(settings_win, width=340, fg_color=PANEL_COLOR, border_color="#2D3748", show="*")
    api_entry.pack(padx=30, pady=(5, 15))
    api_entry.insert(0, app_config.get("api_key", ""))
    
    ctk.CTkLabel(settings_win, text="Model", font=(FONT_UI, 12), text_color=TEXT_MUTED).pack(anchor="w", padx=30)
    model_var = ctk.StringVar(value=app_config.get("model", "gemini-2.5-pro"))
    model_dropdown = ctk.CTkOptionMenu(settings_win, variable=model_var,
                                       values=["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-pro-exp", "gemini-flash-lite-latest"],
                                       width=340, fg_color=PANEL_COLOR, button_color=ACCENT, button_hover_color="#2563EB")
    model_dropdown.pack(padx=30, pady=(5, 20))
    
    def save_settings():
        app_config["api_key"] = api_entry.get().strip()
        app_config["model"] = model_var.get()
        save_config(app_config)
        toast.show("Settings saved!", SUCCESS)
        app.after(2000, toast.hide)
        settings_win.destroy()
        
    save_btn = ctk.CTkButton(settings_win, text="Save Settings", command=save_settings,
                             font=(FONT_UI, 14, "bold"), fg_color=ACCENT, hover_color="#2563EB", height=40)
    save_btn.pack(padx=30, pady=10, fill="x")

ai_btn = ctk.CTkButton(
    sidebar, text="✨  AI Auto-Type  (Ctrl+Shift+Q)", command=on_ai_auto_type,
    font=(FONT_UI, 14, "bold"), fg_color="#8B5CF6",
    hover_color="#7C3AED", height=45,
)
ai_btn.grid(row=3, column=0, padx=20, pady=(20, 10), sticky="ew")
ai_error_btn = ctk.CTkButton(
    sidebar, text="🔧  AI Error Fix  (Ctrl+Shift+E)", command=on_ai_error_fix,
    font=(FONT_UI, 14, "bold"), fg_color="#D97706",
    hover_color="#B45309", height=45,
)
ai_error_btn.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")


start_btn = ctk.CTkButton(
    sidebar, text="▶  Start  (Ctrl+Q)", command=on_start_stop,
    font=(FONT_UI, 14, "bold"), fg_color=ACCENT,
    hover_color="#2563EB", height=45,
)
start_btn.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")

stop_btn = ctk.CTkButton(
    sidebar, text="⏹  Stop",
    command=lambda: on_start_stop() if typing_active else None,
    font=(FONT_UI, 14, "bold"), fg_color=PANEL_COLOR,
    hover_color="#B91C1C", height=45, state="disabled",
)
stop_btn.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="ew")

def remove_indentation():
    text  = code_box.get("1.0", ctk.END)
    lines = [line.lstrip() for line in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    cleaned = "\n".join(lines)
    code_box.delete("1.0", ctk.END)
    code_box.insert("1.0", cleaned)
    toast.show("Indentation removed!", SUCCESS)
    app.after(3000, toast.hide)

# ── Main content ──────────────────────────────────────────────────────────────
main_content = ctk.CTkFrame(app, fg_color="transparent")
main_content.grid(row=0, column=1, padx=30, pady=30, sticky="nsew")
main_content.grid_rowconfigure(1, weight=1)
main_content.grid_columnconfigure(0, weight=1)

header = ctk.CTkFrame(main_content, fg_color="transparent")
header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
ctk.CTkLabel(header, text="Payload Editor",
             font=(FONT_UI, 24, "bold"), text_color="white").pack(side="left")

def paste_code():
    try:
        clipboard = app.clipboard_get()
    except Exception:
        toast.show("Clipboard is empty!", DANGER)
        app.after(3000, toast.hide)
        return
    _placeholder_clear()
    code_box.delete("1.0", ctk.END)
    code_box.insert("1.0", clipboard)
    toast.show("Pasted!", SUCCESS)
    app.after(2000, toast.hide)

dedent_btn = ctk.CTkButton(
    header, text="Remove Indentation", command=remove_indentation,
    font=(FONT_UI, 12, "bold"), fg_color="#1E293B",
    hover_color="#334155", text_color=TEXT_MUTED, height=35,
    border_width=1, border_color="#2D3748",
)
dedent_btn.pack(side="right", padx=(6, 0))

paste_btn = ctk.CTkButton(
    header, text="Paste", command=paste_code,
    font=(FONT_UI, 12, "bold"), fg_color=ACCENT,
    hover_color="#2563EB", text_color="white", height=35,
)
paste_btn.pack(side="right")

PLACEHOLDER       = "// Paste your code payload here\n// Or press your configured hotkey to Auto-Solve!"
PLACEHOLDER_COLOR = "#4B5563"
CODE_COLOR        = "#A5B4FC"
placeholder_active = True

code_box = ctk.CTkTextbox(
    main_content, font=(FONT_CODE, 15), fg_color=PANEL_COLOR,
    text_color=PLACEHOLDER_COLOR, border_color="#2D3748",
    border_width=1, corner_radius=12,
)
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

# ── Accessibility check ───────────────────────────────────────────────────────
def _check_accessibility():
    if not IS_MAC:
        return
    try:
        from ApplicationServices import AXIsProcessTrusted
        if not AXIsProcessTrusted():
            app.after(500, lambda: toast.show(
                "Grant Accessibility: System Settings → Privacy → Accessibility", WARNING
            ))
    except Exception:
        pass

# ── Global hotkeys ────────────────────────────────────────────────────────────
# CGEventTap on main RunLoop — thread-safe, no TSM calls, works globally.
# Fall back to pynput Listener on non-macOS.

def _setup_hotkey_nsevent():
    """Ctrl+Q and Ctrl+Shift+Q via CGEventSourceKeyState polling (thread-safe, GIL-safe, TSM-safe)."""
    app.bind("<Control-q>", lambda e: on_start_stop())
    app.bind("<Command-q>", lambda e: on_start_stop())
    app.bind("<Control-Shift-q>", lambda e: on_ai_auto_type())
    app.bind("<Control-Shift-Q>", lambda e: on_ai_auto_type())
    app.bind("<Control-Q>", lambda e: on_ai_auto_type())
    app.bind("<Command-Shift-q>", lambda e: on_ai_auto_type())
    app.bind("<Command-Shift-Q>", lambda e: on_ai_auto_type())
    app.bind("<Command-Q>", lambda e: on_ai_auto_type())
    app.bind("<Control-Shift-e>", lambda e: on_ai_error_fix())
    app.bind("<Control-Shift-E>", lambda e: on_ai_error_fix())
    app.bind("<Command-Shift-e>", lambda e: on_ai_error_fix())
    app.bind("<Command-Shift-E>", lambda e: on_ai_error_fix())
    app._hotkey_pressed = False
    app._ai_hotkey_pressed = False

    from ApplicationServices import AXIsProcessTrusted
    if not AXIsProcessTrusted():
        app.after(800, lambda: toast.show(
            "Grant Accessibility for AutoTyper in System Settings → Privacy & Security", WARNING
        ))
        return

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
                    on_ai_auto_type()
            elif is_mod and is_shift and e_key:
                if not getattr(app, '_ai_error_hotkey_pressed', False):
                    app._ai_error_hotkey_pressed = True
                    on_ai_error_fix()
            elif is_mod and not is_shift and q:
                if not app._hotkey_pressed and not app._ai_hotkey_pressed:
                    app._hotkey_pressed = True
                    # Delay start_stop slightly to see if the user is rolling into Shift+Q
                    app.after(150, lambda: on_start_stop() if (not app._ai_hotkey_pressed and app._hotkey_pressed) else None)
            else:
                if not (is_mod or q or e_key):
                    app._hotkey_pressed = False
                    app._ai_hotkey_pressed = False
                    app._ai_error_hotkey_pressed = False
        except Exception:
            pass
        app.after(50, poll_hotkey)
        
    app.after(50, poll_hotkey)


def _setup_hotkey_pynput():
    """Fallback: pynput Listener (non-macOS or no AppKit)."""
    def on_activate():
        app.after(0, on_start_stop)
    def on_activate_ai():
        app.after(0, on_ai_auto_type)
    def on_activate_error():
        app.after(0, on_ai_error_fix)

    global _listener
    _listener = pynput_keyboard.GlobalHotKeys({
        '<ctrl>+q': on_activate,
        '<cmd>+q': on_activate,
        '<ctrl>+<shift>+q': on_activate_ai,
        '<ctrl>+<shift>+Q': on_activate_ai,
        '<ctrl>+Q': on_activate_ai,
        '<cmd>+<shift>+q': on_activate_ai,
        '<cmd>+<shift>+Q': on_activate_ai,
        '<cmd>+Q': on_activate_ai,
        '<ctrl>+<shift>+e': on_activate_error,
        '<ctrl>+<shift>+E': on_activate_error,
        '<cmd>+<shift>+e': on_activate_error,
        '<cmd>+<shift>+E': on_activate_error
    })
    _listener.daemon = True
    _listener.start()
    return _listener


# ── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _check_accessibility()
    if IS_MAC and _USE_MACOS_NATIVE:
        _setup_hotkey_nsevent()
    elif _HAS_PYNPUT:
        _setup_hotkey_pynput()
    app.mainloop()

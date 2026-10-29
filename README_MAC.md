# Ai_AutoTyper — macOS Setup Guide

## What changed from the original (Windows) version

| Area | Original | macOS version |
|---|---|---|
| Global hotkeys | `keyboard` library (needs root) | `pynput` (no root needed) |
| Typing engine | `pyautogui.write()` (drops Unicode) | `pynput.keyboard.Controller.type()` |
| Hotkey modifiers | `Ctrl` | `Cmd` |
| Screen size detection | `ctypes.windll.user32` | `tkinter.winfo_screenwidth/height` |
| Fonts | Segoe UI / Consolas | Helvetica Neue / Menlo |
| Clipboard fallback | `pyperclip` only | `pyperclip` → `pbcopy` → tkinter |

## Requirements

```
pip install customtkinter pyautogui pynput mss Pillow google-genai pyperclip
```

Or:

```
pip install -r requirements.txt
```

## Accessibility permission (required)

Both `pynput` and `pyautogui` need Accessibility access to control the keyboard.

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click **+** and add **Terminal** (or your IDE / Python launcher)
3. Toggle it **on**

Without this, global hotkeys and auto-typing will silently do nothing.

## Hotkeys

| Action | Shortcut |
|---|---|
| Start / Stop typing | `Cmd + Q` |
| Capture screen & AI solve | `Cmd + Shift + Q` |
| Fix previous solution from error | `Cmd + Shift + E` |

## Running

```bash
python main.py
```

## config.json

```json
{
    "api_key": "YOUR_GEMINI_API_KEY_HERE",
    "hotkey": "ctrl+shift+q",
    "model": "gemini-2.5-pro",
    "overlay_width": 700,
    "overlay_height": 500,
    "overlay_position": "right"
}
```

The `hotkey` field is kept for reference but ignored on macOS — hotkeys are always `Cmd`-based there.

from pynput import keyboard
from pynput.keyboard import HotKey

hk = HotKey.parse('<ctrl>+<shift>+q')
hotkey = HotKey(hk, lambda: print("Triggered!"))

hotkey.press(keyboard.Key.ctrl)
hotkey.press(keyboard.Key.shift)
hotkey.press(keyboard.KeyCode.from_char('Q')) # When shift is pressed, char is usually uppercase
print("With 'Q':", hotkey._state)

hotkey.release(keyboard.KeyCode.from_char('Q'))
hotkey.press(keyboard.KeyCode.from_char('q'))
print("With 'q':", hotkey._state)

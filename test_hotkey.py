from pynput import keyboard
import time

def on_activate():
    print("Global hotkey activated!")

def for_canonical(f):
    return lambda k: f(listener.canonical(k))

hotkey = keyboard.HotKey(
    keyboard.HotKey.parse('<ctrl>+q'),
    on_activate)

listener = keyboard.Listener(
    on_press=for_canonical(hotkey.press),
    on_release=for_canonical(hotkey.release))
listener.start()

print("Listening for <ctrl>+q...")
time.sleep(5)

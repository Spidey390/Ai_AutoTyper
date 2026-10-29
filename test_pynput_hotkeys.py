from pynput import keyboard
import time

def on_activate():
    print("Ctrl+Q activated!")

def on_activate_ai():
    print("Ctrl+Shift+Q activated!")

listener = keyboard.GlobalHotKeys({
    '<ctrl>+q': on_activate,
    '<ctrl>+<shift>+q': on_activate_ai
})
listener.daemon = True
listener.start()

print("Listening for 3 seconds...")
time.sleep(3)

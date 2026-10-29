from pynput import keyboard
from pynput.keyboard import HotKey

try:
    print(HotKey.parse('<ctrl>+<shift>+q'))
except Exception as e:
    print("Error:", e)

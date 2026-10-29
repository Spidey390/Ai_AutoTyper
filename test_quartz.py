import time
import Quartz
import sys

_RETURN_KEYCODE = 36
_TAB_KEYCODE    = 48

def _post_quartz_char(char: str):
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

print("Will type in 3 seconds...")
time.sleep(3)
for c in "Hello\n":
    _post_quartz_char(c)
    time.sleep(0.1)
print("Done")

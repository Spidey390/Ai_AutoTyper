import time
import Quartz

_RETURN_KEYCODE = 36
_TAB_KEYCODE    = 48

def _post_quartz_char(char: str):
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    if char == "\n":
        for down in (True, False):
            e = Quartz.CGEventCreateKeyboardEvent(src, _RETURN_KEYCODE, down)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)
    elif char == "\t":
        for down in (True, False):
            e = Quartz.CGEventCreateKeyboardEvent(src, _TAB_KEYCODE, down)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)
    else:
        for down in (True, False):
            e = Quartz.CGEventCreateKeyboardEvent(src, 0xFFFF, down)
            Quartz.CGEventKeyboardSetUnicodeString(e, len(char), char)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)

time.sleep(2)
_post_quartz_char("a")
_post_quartz_char("b")
_post_quartz_char("c")
_post_quartz_char("\n")

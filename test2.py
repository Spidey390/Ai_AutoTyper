import Quartz
src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
down = Quartz.CGEventCreateKeyboardEvent(src, 0, True)
Quartz.CGEventKeyboardSetUnicodeString(down, 1, 'x')
Quartz.CGEventPost(Quartz.kCGSessionEventTap, down)
up = Quartz.CGEventCreateKeyboardEvent(src, 0, False)
Quartz.CGEventKeyboardSetUnicodeString(up, 1, 'x')
Quartz.CGEventPost(Quartz.kCGSessionEventTap, up)

import Quartz
import sys

event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
_cgeventtap = Quartz.CGEventTapCreate(
    Quartz.kCGHIDEventTap,
    Quartz.kCGHeadInsertEventTap,
    Quartz.kCGEventTapOptionListenOnly,
    event_mask,
    lambda proxy, type, event, refcon: event,
    None,
)

if _cgeventtap is None:
    print("CGEventTapCreate returned None. Accessibility permission is missing!")
else:
    print("CGEventTapCreate succeeded. Accessibility permission is granted!")

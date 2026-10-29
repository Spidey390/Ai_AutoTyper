import Quartz
import sys

def _tap_callback(proxy, event_type, event, refcon):
    print("Tap callback fired!")
    return event

event_mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
_cgeventtap = Quartz.CGEventTapCreate(
    Quartz.kCGHIDEventTap,
    Quartz.kCGHeadInsertEventTap,
    Quartz.kCGEventTapOptionListenOnly,
    event_mask,
    _tap_callback,
    None,
)

if _cgeventtap is None:
    print("CGEventTapCreate returned None.")
else:
    print("CGEventTapCreate succeeded.")
    
    # We can try to attach it to the run loop
    source = Quartz.CFMachPortCreateRunLoopSource(None, _cgeventtap, 0)
    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetMain(),
        source,
        Quartz.kCFRunLoopCommonModes,
    )
    Quartz.CGEventTapEnable(_cgeventtap, True)
    
    print("Starting CFRunLoop...")
    import time
    # Just run it a bit
    Quartz.CFRunLoopRun()

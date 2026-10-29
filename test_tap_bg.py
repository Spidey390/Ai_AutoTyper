import Quartz
import threading
import time

def background_tap():
    print("Background thread started.")
    NSControlKeyMask = 1 << 18
    Q_KEYCODE = 12

    def _tap_callback(proxy, event_type, event, refcon):
        try:
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode
            )
            flags = Quartz.CGEventGetFlags(event)
            if keycode == Q_KEYCODE and (flags & NSControlKeyMask):
                print("Ctrl+Q pressed globally!")
        except Exception as e:
            print("Error in callback:", e)
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
        print("Failed to create CGEventTap in background thread.")
        return

    source = Quartz.CFMachPortCreateRunLoopSource(None, _cgeventtap, 0)
    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetCurrent(),
        source,
        Quartz.kCFRunLoopCommonModes,
    )
    Quartz.CGEventTapEnable(_cgeventtap, True)
    print("Running CFRunLoop in background thread...")
    Quartz.CFRunLoopRun()

t = threading.Thread(target=background_tap, daemon=True)
t.start()

print("Main thread sleeping for 5 seconds...")
time.sleep(5)
print("Main thread done.")

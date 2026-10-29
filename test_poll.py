import Quartz
import time

def poll():
    print("Hold Ctrl and Q...")
    for _ in range(50):
        ctrl = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 59)
        q = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 12)
        if ctrl and q:
            print("Ctrl+Q detected!")
            return
        time.sleep(0.1)
    print("Not detected.")

poll()

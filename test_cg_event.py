import Quartz
import time

print("Listening for 5 seconds...")
for _ in range(50):
    q = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 12)
    ctrl = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 59)
    shift = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 56)
    if q or ctrl or shift:
        print(f"q={q}, ctrl={ctrl}, shift={shift}")
    time.sleep(0.1)

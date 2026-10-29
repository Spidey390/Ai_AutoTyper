from setuptools import setup

APP      = ["main.py"]
OPTIONS  = {
    "argv_emulation": False,
    "packages": [
        "customtkinter",
        "pynput",
        "PIL",
        "AppKit",
        "Quartz",
        "Foundation",
        "CoreFoundation",
        "objc",
        "darkdetect",
    ],
    "includes": [
        "ApplicationServices",
    ],
    "plist": {
        "CFBundleName":             "AutoTyper",
        "CFBundleDisplayName":      "AutoTyper",
        "CFBundleIdentifier":       "com.autotyper.app",
        "CFBundleVersion":          "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "NSHighResolutionCapable":  True,
        "LSUIElement":              False,
        "NSAppleEventsUsageDescription": "AutoTyper needs Accessibility access to type text.",
    },
    "excludes": [
        "google",
        "mss",
        "pyautogui",
    ],
}

setup(
    name="AutoTyper",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

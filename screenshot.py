"""
screenshot.py — Silent screen capture using mss.
Captures the primary monitor with zero visual disturbance.
"""

import io
import base64
import mss
from PIL import Image


def capture_screen_image() -> tuple[Image.Image, Image.Image]:
    """
    Silently captures the primary monitor.
    Returns:
        - PIL Image object of full resolution (for Gemini API)
        - PIL Image object (for preview thumbnail)
    """
    with mss.mss() as sct:
        # Capture primary monitor (index 1)
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)

        # Convert to PIL image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        # Create thumbnail for preview
        thumbnail = img.copy()
        thumbnail.thumbnail((400, 300))

        return img, thumbnail

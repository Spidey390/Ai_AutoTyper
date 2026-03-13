"""
screenshot.py — Silent screen capture using mss.
Captures the primary monitor with zero visual disturbance.
"""

import io
import base64
import mss
from PIL import Image


def capture_screen_base64() -> tuple[str, Image.Image]:
    """
    Silently captures the primary monitor.
    Returns:
        - base64 encoded PNG string (for Gemini API)
        - PIL Image object (for preview thumbnail)
    """
    with mss.mss() as sct:
        # Capture primary monitor (index 1)
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)

        # Convert to PIL image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        # Encode to base64 PNG
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        img_bytes = buffer.getvalue()
        b64_str = base64.b64encode(img_bytes).decode("utf-8")

        # Create thumbnail for preview
        thumbnail = img.copy()
        thumbnail.thumbnail((400, 300))

        return b64_str, thumbnail

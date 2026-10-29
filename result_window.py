"""
result_window.py — Floating solution overlay using tkinter.
Appears on top of all windows WITHOUT stealing focus from the active app.
macOS-compatible: uses tkinter screen geometry instead of ctypes/windll.
"""

import threading
import tkinter as tk
from tkinter import scrolledtext
import re
import sys

try:
    import pyperclip
    _HAS_PYPERCLIP = True
except ImportError:
    _HAS_PYPERCLIP = False


# ── Color palette ──────────────────────────────────────────────
BG_DARK      = "#0d0d0d"
BG_CARD      = "#141414"
BG_CODE      = "#1a1a2e"
ACCENT       = "#6c63ff"
ACCENT2      = "#a78bfa"
TEXT_PRIMARY = "#f0f0f0"
TEXT_MUTED   = "#888888"
SUCCESS      = "#10b981"
ERROR_COL    = "#ef4444"
BORDER       = "#2a2a2a"

FONT_MONO    = ("Menlo", 11) if sys.platform == "darwin" else ("Consolas", 11)
FONT_BODY    = ("Helvetica Neue", 11) if sys.platform == "darwin" else ("Segoe UI", 11)
FONT_TITLE   = ("Helvetica Neue", 13, "bold") if sys.platform == "darwin" else ("Segoe UI", 13, "bold")
FONT_SMALL   = ("Helvetica Neue", 9) if sys.platform == "darwin" else ("Segoe UI", 9)


class ResultWindow:
    """Floating overlay window that shows Gemini solution."""

    def __init__(self, width: int = 700, height: int = 550, position: str = "right"):
        self.width    = width
        self.height   = height
        self.position = position
        self.root: tk.Tk | None = None
        self._current_code = ""

    # ── Public API ─────────────────────────────────────────────

    def show_loading(self):
        """Show the window with a loading indicator."""
        threading.Thread(target=self._launch_loading, daemon=True).start()

    def show_result(self, markdown_text: str):
        """Update the window with the Gemini response."""
        if self.root:
            self.root.after(0, lambda: self._render_result(markdown_text))

    def show_error(self, error_msg: str):
        """Show an error in the overlay."""
        if self.root:
            self.root.after(0, lambda: self._render_error(error_msg))

    def update_status(self, msg: str):
        """Update the loading message live (e.g. 'Retrying in 16s...')."""
        if self.root and hasattr(self, "spinner_label"):
            try:
                self.root.after(0, lambda: self._update_loading_text(msg))
            except Exception:
                pass

    def close(self):
        if self.root:
            self.root.after(0, self.root.destroy)
            self.root = None

    # ── Internal ───────────────────────────────────────────────

    def _calc_position(self, root: tk.Tk):
        """Calculate overlay position using tkinter (cross-platform)."""
        root.update_idletasks()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()

        margin = 20
        y = (screen_h - self.height) // 2

        if self.position == "right":
            x = screen_w - self.width - margin
        else:
            x = margin

        return x, y

    def _launch_loading(self):
        """Create the root window and show loading state."""
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass

        self.root = tk.Tk()
        root = self.root

        # ── Window setup ──────────────────────────────────────
        root.title("Gemini Solver")
        root.configure(bg=BG_DARK)
        root.resizable(True, True)

        # Position window (must be done after tk.Tk() so screen info is available)
        x, y = self._calc_position(root)
        root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        # Stay on top — works on macOS, Windows, Linux
        root.attributes("-topmost", True)

        # Slight transparency (macOS supports -alpha natively)
        try:
            root.attributes("-alpha", 0.97)
        except tk.TclError:
            pass  # Some Linux WMs don't support alpha

        self._build_ui(root)
        self._set_loading_state(True)

        root.mainloop()
        self.root = None

    def _build_ui(self, root: tk.Tk):
        """Build the full UI layout."""
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # ── Title bar ─────────────────────────────────────────
        title_bar = tk.Frame(root, bg=BG_CARD, pady=10, padx=15)
        title_bar.grid(row=0, column=0, sticky="ew")
        title_bar.columnconfigure(1, weight=1)

        canvas = tk.Canvas(title_bar, width=28, height=28, bg=BG_CARD,
                           highlightthickness=0)
        canvas.create_oval(2, 2, 26, 26, fill=ACCENT, outline="")
        canvas.create_text(14, 14, text="G", fill="white",
                           font=(FONT_TITLE[0], 12, "bold"))
        canvas.grid(row=0, column=0, padx=(0, 10))

        self.title_label = tk.Label(
            title_bar, text="✨ Gemini Solver — Analyzing...",
            font=FONT_TITLE, bg=BG_CARD, fg=TEXT_PRIMARY, anchor="w"
        )
        self.title_label.grid(row=0, column=1, sticky="w")

        close_btn = tk.Button(
            title_bar, text="✕", font=FONT_SMALL,
            bg=BG_CARD, fg=TEXT_MUTED, relief="flat", cursor="hand2",
            activebackground=ERROR_COL, activeforeground="white",
            command=root.destroy, padx=8, pady=2
        )
        close_btn.grid(row=0, column=2)

        tk.Frame(root, bg=BORDER, height=1).grid(row=0, column=0, sticky="ew")

        # ── Content area ──────────────────────────────────────
        content = tk.Frame(root, bg=BG_DARK)
        content.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        # Loading frame
        self.loading_frame = tk.Frame(content, bg=BG_DARK)
        self.loading_frame.grid(row=0, column=0, sticky="nsew")
        self.loading_frame.columnconfigure(0, weight=1)
        self.loading_frame.rowconfigure(0, weight=1)

        loading_inner = tk.Frame(self.loading_frame, bg=BG_DARK)
        loading_inner.place(relx=0.5, rely=0.5, anchor="center")

        self.spinner_label = tk.Label(
            loading_inner, text="⟳", font=(FONT_BODY[0], 36),
            bg=BG_DARK, fg=ACCENT
        )
        self.spinner_label.pack()

        tk.Label(
            loading_inner, text="Taking screenshot & querying Gemini...",
            font=FONT_BODY, bg=BG_DARK, fg=TEXT_MUTED
        ).pack(pady=(10, 0))

        tk.Label(
            loading_inner, text="This will appear without disturbing your screen.",
            font=FONT_SMALL, bg=BG_DARK, fg=TEXT_MUTED
        ).pack(pady=(4, 0))

        # Result frame
        self.result_frame = tk.Frame(content, bg=BG_DARK)
        self.result_frame.grid(row=0, column=0, sticky="nsew")
        self.result_frame.columnconfigure(0, weight=1)
        self.result_frame.rowconfigure(0, weight=1)

        self.text_area = scrolledtext.ScrolledText(
            self.result_frame,
            font=FONT_BODY,
            bg=BG_DARK, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat", bd=0,
            padx=20, pady=16,
            wrap=tk.WORD,
            state="disabled"
        )
        self.text_area.grid(row=0, column=0, sticky="nsew")

        self.text_area.tag_configure("heading",
            font=(FONT_BODY[0], 13, "bold"), foreground=ACCENT2, spacing3=6)
        self.text_area.tag_configure("bold",
            font=(FONT_BODY[0], 11, "bold"), foreground=TEXT_PRIMARY)
        self.text_area.tag_configure("code_block",
            font=FONT_MONO, background=BG_CODE, foreground="#e2e8f0",
            lmargin1=16, lmargin2=16, rmargin=16, spacing1=8, spacing3=8)
        self.text_area.tag_configure("inline_code",
            font=FONT_MONO, background="#2d2d3a", foreground="#f472b6")
        self.text_area.tag_configure("muted",
            foreground=TEXT_MUTED, font=FONT_SMALL)
        self.text_area.tag_configure("normal",
            foreground=TEXT_PRIMARY, font=FONT_BODY)
        self.text_area.tag_configure("bullet",
            foreground=ACCENT2, font=FONT_BODY)

        # ── Bottom bar ────────────────────────────────────────
        bottom = tk.Frame(root, bg=BG_CARD, pady=8, padx=15)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(1, weight=1)

        self.copy_btn = tk.Button(
            bottom, text="📋  Copy Code", font=FONT_SMALL,
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            activebackground=ACCENT2, activeforeground="white",
            command=self._copy_code, padx=14, pady=6
        )
        self.copy_btn.grid(row=0, column=0, padx=(0, 8))

        self.status_label = tk.Label(
            bottom, text="Press configured hotkey to capture a new screenshot",
            font=FONT_SMALL, bg=BG_CARD, fg=TEXT_MUTED, anchor="w"
        )
        self.status_label.grid(row=0, column=1, sticky="w")

        close_btn2 = tk.Button(
            bottom, text="Close", font=FONT_SMALL,
            bg=BORDER, fg=TEXT_MUTED, relief="flat", cursor="hand2",
            activebackground=ERROR_COL, activeforeground="white",
            command=root.destroy, padx=12, pady=6
        )
        close_btn2.grid(row=0, column=2)

        self._set_loading_state(True)
        self._animate_spinner(0)

    def _update_loading_text(self, msg: str):
        try:
            if hasattr(self, "_loading_status_label"):
                self._loading_status_label.config(text=msg)
        except Exception:
            pass

    def _animate_spinner(self, step: int):
        frames = ["⟳", "◐", "◓", "◑", "◒"]
        if self.root and hasattr(self, "spinner_label"):
            try:
                self.spinner_label.config(text=frames[step % len(frames)])
                self.root.after(150, self._animate_spinner, step + 1)
            except Exception:
                pass

    def _set_loading_state(self, loading: bool):
        if loading:
            self.loading_frame.lift()
        else:
            self.result_frame.lift()

    def _render_result(self, markdown_text: str):
        self.title_label.config(text="✨ Gemini Solver — Solution Ready")
        self._set_loading_state(False)

        ta = self.text_area
        ta.config(state="normal")
        ta.delete("1.0", tk.END)

        code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", markdown_text, re.DOTALL)
        self._current_code = "\n\n".join(code_blocks) if code_blocks else markdown_text

        lines = markdown_text.split("\n")
        in_code_block = False
        code_lang = ""

        for line in lines:
            if line.startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_lang = line[3:].strip()
                    ta.insert(tk.END, f"  ─── {code_lang or 'code'} ───\n", "muted")
                else:
                    in_code_block = False
                    ta.insert(tk.END, "\n")
                continue

            if in_code_block:
                ta.insert(tk.END, line + "\n", "code_block")
                continue

            if line.startswith("### "):
                ta.insert(tk.END, line[4:] + "\n", "heading")
            elif line.startswith("## "):
                ta.insert(tk.END, line[3:] + "\n", "heading")
            elif line.startswith("# "):
                ta.insert(tk.END, line[2:] + "\n", "heading")
            elif "**" in line:
                self._insert_bold_line(ta, line)
            elif line.startswith("- ") or line.startswith("* "):
                ta.insert(tk.END, "  • ", "bullet")
                ta.insert(tk.END, line[2:] + "\n", "normal")
            elif line.strip() == "":
                ta.insert(tk.END, "\n")
            else:
                ta.insert(tk.END, line + "\n", "normal")

        ta.config(state="disabled")
        ta.see("1.0")
        self.status_label.config(text="✅ Solution ready — Press hotkey for a new capture")

    def _insert_bold_line(self, ta, line: str):
        parts = re.split(r"(\*\*.*?\*\*)", line)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                ta.insert(tk.END, part[2:-2], "bold")
            else:
                ta.insert(tk.END, part, "normal")
        ta.insert(tk.END, "\n")

    def _render_error(self, error_msg: str):
        self.title_label.config(text="⚠ Gemini Solver — Error")
        self._set_loading_state(False)

        ta = self.text_area
        ta.config(state="normal")
        ta.delete("1.0", tk.END)
        ta.tag_configure("error",
            foreground=ERROR_COL, font=FONT_BODY, spacing1=10)
        ta.insert(tk.END, "Something went wrong:\n\n", "heading")
        ta.insert(tk.END, str(error_msg), "error")
        ta.insert(tk.END, "\n\nPlease check:\n", "bold")
        ta.insert(tk.END, "  • Your API key in config.json\n", "normal")
        ta.insert(tk.END, "  • Internet connection\n", "normal")
        ta.insert(tk.END, "  • Gemini API quota\n", "normal")
        ta.config(state="disabled")

    def _copy_code(self):
        if not self._current_code:
            self.status_label.config(text="No code found to copy.")
            return

        copied = False
        # Try pyperclip first
        if _HAS_PYPERCLIP:
            try:
                pyperclip.copy(self._current_code)
                copied = True
            except Exception:
                pass

        # macOS fallback: pbcopy
        if not copied and sys.platform == "darwin":
            try:
                import subprocess
                proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                proc.communicate(self._current_code.encode("utf-8"))
                copied = True
            except Exception:
                pass

        # tkinter clipboard fallback
        if not copied and self.root:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(self._current_code)
                copied = True
            except Exception:
                pass

        if copied:
            self.status_label.config(text="✅ Code copied to clipboard!")
            if self.root:
                self.root.after(3000, lambda: self.status_label.config(
                    text="Press hotkey to capture a new screenshot"))
        else:
            self.status_label.config(text="⚠ Could not copy — try installing pyperclip.")

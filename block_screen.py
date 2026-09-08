# block_screen.py — Fullscreen Block Window
# Shown when adult content is detected. Cannot be minimized or closed
# without clicking the "Go Back" button.

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import os


import win32gui
import win32con
import win32process
import psutil


class BlockScreen:
    """
    A fullscreen, always-on-top blocking window.
    The user can only dismiss it by clicking the 'Go Back' button,
    which automatically closes the adult browser window.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, root, blocked_title: str = "", matched_keyword: str = "", target_hwnd: int = 0):
        self.root = root
        self.blocked_title = blocked_title
        self.matched_keyword = matched_keyword
        self.target_hwnd = target_hwnd
        self._dismissed = False
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        """Configure the root window as a fullscreen overlay."""
        self.root.title("ACCESS BLOCKED — Adult Content Blocker")
        self.root.configure(bg="#0a0000")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(False)  # Keep title bar for accessibility
        self.root.resizable(False, False)

        # Prevent Alt+F4 from closing the window
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        # Prevent keyboard shortcuts from escaping
        self.root.bind("<Alt-F4>", lambda e: "break")
        self.root.bind("<Escape>", lambda e: "break")
        self.root.bind("<F11>", lambda e: "break")

        # Handle window destruction event to clean up instance lock
        self.root.bind("<Destroy>", self._on_destroy)

        # Keep window on top — re-apply every second
        self._keep_on_top()

    def _on_destroy(self, event=None):
        """Clean up singleton instance lock when window is destroyed."""
        self._dismissed = True
        with BlockScreen._lock:
            BlockScreen._instance = None

    def _keep_on_top(self):
        """Periodically re-assert the window stays on top."""
        if not self._dismissed:
            try:
                if self.root.winfo_exists():
                    self.root.attributes("-topmost", True)
                    self.root.lift()
                    self.root.focus_force()
                    self.root.after(500, self._keep_on_top)
            except Exception:
                pass

    def _on_close_attempt(self):
        """Called when user tries to close the window — ignore it."""
        try:
            if not self._dismissed and self.root.winfo_exists():
                self.root.attributes("-topmost", True)
                self.root.lift()
        except Exception:
            pass

    def _build_ui(self):
        """Build the block screen UI."""
        # === Main container ===
        main = tk.Frame(self.root, bg="#0a0000")
        main.place(relx=0, rely=0, relwidth=1, relheight=1)

        # === Animated gradient background ===
        self.canvas = tk.Canvas(main, bg="#0a0000", highlightthickness=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._animate_bg()

        # === Content frame (centered) ===
        content = tk.Frame(self.canvas, bg="#1a0000", relief="flat",
                           bd=0, padx=60, pady=50)
        content.place(relx=0.5, rely=0.5, anchor="center")

        # Add glowing border effect via an outer frame
        border = tk.Frame(self.canvas, bg="#ff2222", bd=3)
        border.place(relx=0.5, rely=0.5, anchor="center")
        inner = tk.Frame(border, bg="#1a0000", padx=60, pady=50)
        inner.pack()

        # === Shield icon (unicode) ===
        icon_label = tk.Label(
            inner, text="🛡", font=("Segoe UI Emoji", 72),
            bg="#1a0000", fg="#ff4444"
        )
        icon_label.pack(pady=(10, 5))

        # === Main title ===
        title_font = tkfont.Font(family="Segoe UI", size=36, weight="bold")
        title = tk.Label(
            inner, text="ACCESS BLOCKED",
            font=title_font, bg="#1a0000", fg="#ff3333"
        )
        title.pack(pady=(0, 5))

        # === Divider ===
        divider = tk.Frame(inner, bg="#ff3333", height=2, width=400)
        divider.pack(pady=10, fill="x")

        # === Subtitle ===
        subtitle_font = tkfont.Font(family="Segoe UI", size=14)
        subtitle = tk.Label(
            inner,
            text="⚠  This website contains adult/explicit content\nand has been blocked by your system administrator.",
            font=subtitle_font, bg="#1a0000", fg="#ffaaaa",
            justify="center"
        )
        subtitle.pack(pady=(5, 10))

        # === Matched keyword info ===
        if self.matched_keyword:
            kw_font = tkfont.Font(family="Consolas", size=11)
            kw_label = tk.Label(
                inner,
                text=f'Detected: "{self.matched_keyword}"',
                font=kw_font, bg="#1a0000", fg="#ff6666",
                justify="center"
            )
            kw_label.pack(pady=3)

        # === Blocked title (if available) ===
        if self.blocked_title and len(self.blocked_title) < 120:
            title_font2 = tkfont.Font(family="Consolas", size=10)
            blocked_lbl = tk.Label(
                inner,
                text=f'Page: "{self.blocked_title[:80]}{"..." if len(self.blocked_title) > 80 else ""}"',
                font=title_font2, bg="#1a0000", fg="#cc4444",
                justify="center"
            )
            blocked_lbl.pack(pady=3)

        # === Spacer ===
        tk.Label(inner, text="", bg="#1a0000").pack(pady=8)

        # === Warning message ===
        warn_font = tkfont.Font(family="Segoe UI", size=12)
        warn = tk.Label(
            inner,
            text="Close this tab and navigate away from adult content.",
            font=warn_font, bg="#1a0000", fg="#ff8888",
            justify="center"
        )
        warn.pack(pady=5)

        # === Go Back / Exit button ===
        btn_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.exit_btn = tk.Button(
            inner,
            text="  ✕  Close & Go Back  ",
            font=btn_font,
            bg="#cc0000",
            fg="white",
            activebackground="#ff2222",
            activeforeground="white",
            relief="flat",
            padx=30,
            pady=12,
            cursor="hand2",
            bd=0,
            command=self._dismiss
        )
        self.exit_btn.pack(pady=(20, 10))

        # Hover effect on button
        self.exit_btn.bind("<Enter>", lambda e: self.exit_btn.config(bg="#ff2222"))
        self.exit_btn.bind("<Leave>", lambda e: self.exit_btn.config(bg="#cc0000"))

        # === Footer ===
        footer_font = tkfont.Font(family="Segoe UI", size=9)
        footer = tk.Label(
            inner,
            text="Adult Content Blocker — Running in background",
            font=footer_font, bg="#1a0000", fg="#552222"
        )
        footer.pack(pady=(15, 5))

        # Pulse animation on the title
        self._pulse_title(title)

    def _pulse_title(self, label):
        """Pulse the title color for a warning effect."""
        colors = ["#ff3333", "#ff6666", "#ff3333", "#cc0000"]
        idx = [0]

        def pulse():
            if not self._dismissed:
                try:
                    if label.winfo_exists() and self.root.winfo_exists():
                        label.config(fg=colors[idx[0] % len(colors)])
                        idx[0] += 1
                        self.root.after(500, pulse)
                except Exception:
                    pass

        pulse()

    def _animate_bg(self):
        """Subtle red pulse animation on the canvas background."""
        shades = ["#0a0000", "#120000", "#0a0000", "#0f0000"]
        idx = [0]

        def step():
            if not self._dismissed:
                try:
                    if self.canvas.winfo_exists() and self.root.winfo_exists():
                        self.canvas.config(bg=shades[idx[0] % len(shades)])
                        idx[0] += 1
                        self.root.after(800, step)
                except Exception:
                    pass

        step()

    def _close_target_window(self):
        """Close the adult browser tab cleanly using WM_CLOSE to prevent crash-restore loops."""
        if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            try:
                win32gui.PostMessage(self.target_hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception as e:
                print(f"[BLOCK] Error closing browser window: {e}")

    def _dismiss(self):
        """Dismiss the block screen and close the adult browser window."""
        self._dismissed = True
        self._close_target_window()
        try:
            self.root.destroy()
        except Exception:
            pass
        finally:
            with BlockScreen._lock:
                BlockScreen._instance = None

    @classmethod
    def show(cls, parent=None, blocked_title: str = "", matched_keyword: str = "", target_hwnd: int = 0):
        """
        Class method to show the block screen overlay.
        Must be called on the main Tk thread (or marshaled via root.after).
        """
        with cls._lock:
            if cls._instance is not None:
                return  # Block screen is already active
            cls._instance = True

        try:
            if parent is not None:
                win = tk.Toplevel(parent)
            else:
                win = tk.Tk()
            screen = cls(win, blocked_title, matched_keyword, target_hwnd)
            win.focus_force()
            if parent is None:
                win.mainloop()
        except Exception as e:
            print(f"[BLOCK] BlockScreen GUI error: {e}")
            with cls._lock:
                cls._instance = None


if __name__ == "__main__":
    # Test the block screen standalone
    BlockScreen.show(blocked_title="Test Adult Site - Example.com", matched_keyword="porn")


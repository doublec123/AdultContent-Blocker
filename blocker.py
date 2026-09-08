# blocker.py — Main Application Entry Point & Background Service
# Runs the system tray icon, background title monitor, and hosts manager.
# NOTE: This application is PERMANENTLY ACTIVE in the system tray.
#
# Protection model:
#   • STEALTH  — The process is disguised in Task Manager as a Windows system
#               service name (random each launch) so it cannot be identified.
#   • DACL    — Kernel-level DACL blocks every "End Task" attempt silently.
#               Task Manager shows Access Denied; no dialog appears.
#   • WATCHDOG — Mutual guardian restarts the process in <500ms if ever killed.
# System shutdown and logoff events pass through cleanly to allow normal Windows
# rebooting, with protection autostarting on boot via Task Scheduler / Startup.

import os
import sys
import secrets
import string
import threading
import time
import tkinter as tk
from PIL import Image, ImageDraw

class NullWriter:
    def write(self, s):
        pass
    def flush(self):
        pass

# Ensure print() statements never crash when running under windowless pythonw.exe
for _attr in ('stdout', 'stderr'):
    try:
        _stream = getattr(sys, _attr)
        if _stream is None:
            raise OSError("Stream is None")
        _stream.write("")
        _stream.flush()
    except Exception:
        setattr(sys, _attr, NullWriter())

# Local module imports
import subprocess
from blocklist import get_all_domains, get_all_keywords
from config import get_setting, load_config, set_password
from hosts_manager import is_admin, apply_blocks, remove_blocks, request_admin
from title_monitor import TitleMonitor
from block_screen import BlockScreen
from admin_panel import open_admin_panel
from autostart import enable_autostart
from process_shield import apply_all_shields

import pystray
from pystray import MenuItem as item

try:
    import win32api
    import win32con
    import win32gui
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False


def get_base_dir() -> str:
    """Get absolute path to application root directory, handling PyInstaller frozen executables."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def create_tray_icon():
    """Create a high-resolution tray icon image (shield icon)."""
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Shield shape points
    shape = [(32, 4), (56, 16), (56, 36), (32, 60), (8, 36), (8, 16)]
    draw.polygon(shape, fill=(204, 0, 0, 255), outline=(255, 66, 66, 255), width=2)

    # Cross / X sign in center
    draw.line((24, 24, 40, 40), fill=(255, 255, 255, 255), width=4)
    draw.line((40, 24, 24, 40), fill=(255, 255, 255, 255), width=4)
    
    return image


class AdultBlockerApp:
    def __init__(self):
        self.root = None
        self.tray_icon = None
        self.monitor = None

    def on_blocked(self, title: str, matched_keyword: str, target_hwnd: int = 0):
        """Callback triggered when adult title is detected."""
        if get_setting("enabled"):
            print(f"[BLOCK] Detected adult content in title: '{title}' (Matched: '{matched_keyword}', HWND: {target_hwnd})")
            
            # Immediately attempt to close the offending tab cleanly with Ctrl+W
            if target_hwnd:
                try:
                    import win32gui, win32con, win32api
                    try:
                        win32gui.SetForegroundWindow(target_hwnd)
                        time.sleep(0.05)
                    except Exception:
                        pass
                    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                    win32api.keybd_event(ord('W'), 0, 0, 0)
                    win32api.keybd_event(ord('W'), 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.1)
                    if win32gui.IsWindow(target_hwnd):
                        win32gui.PostMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
                except Exception:
                    pass

            if self.root:
                self.root.after(0, lambda: BlockScreen.show(parent=self.root, blocked_title=title, matched_keyword=matched_keyword, target_hwnd=target_hwnd))
            else:
                BlockScreen.show(blocked_title=title, matched_keyword=matched_keyword, target_hwnd=target_hwnd)

    def start_background_services(self):
        """Apply hosts blocks and start title monitor."""
        print("[SERVICE] Initializing Adult Content Protection...")
        
        # 1. Apply Hosts DNS Blocking if running as admin
        if is_admin():
            if get_setting("enabled") and get_setting("block_hosts"):
                print("[SERVICE] Applying hosts file DNS blocking...")
                success, count = apply_blocks()
                if success:
                    print(f"[SERVICE] Blocked {count} adult domains in hosts file.")
                else:
                    print("[SERVICE] Failed to update hosts file.")
        else:
            print("[WARNING] Not running as Administrator. Hosts-file DNS blocking is disabled.")
            print("[WARNING] Browser tab title scanner is still active.")

        # 2. Start title monitor thread
        self.monitor = TitleMonitor(self.on_blocked)
        self.monitor.start()
        print("[SERVICE] Browser tab title scanner active.")

        # 3. Start 5-second password randomizer thread
        def randomize_password_loop():
            print("[SERVICE] Password auto-randomizer thread active (changes every 5 seconds).")
            alphabet = string.ascii_letters + string.digits
            while True:
                time.sleep(5)
                if get_setting("randomize_password"):
                    new_pass = "".join(secrets.choice(alphabet) for _ in range(16))
                    set_password(new_pass)

        t_rand = threading.Thread(target=randomize_password_loop, daemon=True)
        t_rand.start()

    def show_admin(self):
        """Open the admin panel UI safely on the main Tk thread."""
        if self.root:
            self.root.after(0, lambda: open_admin_panel(self.root))
        else:
            open_admin_panel()

    def _setup_ctrl_handler(self):
        """
        Set up console Ctrl handler to allow Windows shutdown/logoff to pass through cleanly
        without stalling system reboot or popping up exit dialogs.
        """
        if not _WIN32_AVAILABLE:
            return

        def _handler(event):
            # CTRL_SHUTDOWN_EVENT (4, 6) or CTRL_LOGOFF_EVENT (5):
            # Return False so Windows shuts down/logs off smoothly without prompt
            if event in (4, 5, 6):
                return False
            # For console termination, consume event to prevent unexpected console kill
            return True

        try:
            win32api.SetConsoleCtrlHandler(_handler, True)
            print("[SHIELD] Console Ctrl-handler configured for clean OS shutdown.")
        except Exception as e:
            print(f"[WARNING] Could not install Ctrl-handler: {e}")

    def _start_guardian_supervisor(self):
        """Start background thread to monitor and maintain the mutual guardian process."""
        def _supervisor_loop():
            base_dir = get_base_dir()
            my_pid = os.getpid()
            
            def _get_guardian_cmd():
                exe_path = os.path.join(base_dir, "WindowsSecurityGuardian.exe")
                if os.path.exists(exe_path):
                    return [exe_path, "--target-pid", str(my_pid)]
                script_path = os.path.join(base_dir, "guardian.py")
                python_dir = os.path.dirname(sys.executable)
                pythonw_path = os.path.join(python_dir, "pythonw.exe")
                if not os.path.exists(pythonw_path):
                    pythonw_path = sys.executable
                return [pythonw_path, script_path, "--target-pid", str(my_pid)]

            guardian_proc = None
            while True:
                try:
                    if guardian_proc is None or guardian_proc.poll() is not None:
                        cmd = _get_guardian_cmd()
                        creationflags = 0
                        if sys.platform == "win32":
                            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                        guardian_proc = subprocess.Popen(
                            cmd,
                            cwd=base_dir,
                            creationflags=creationflags,
                            close_fds=True
                        )
                        print(f"[SHIELD] Spawned mutual guardian supervisor (PID {guardian_proc.pid})")
                    time.sleep(2)
                except Exception:
                    time.sleep(2)

        t_sup = threading.Thread(target=_supervisor_loop, daemon=True)
        t_sup.start()

    def run(self):
        # 1. Install security shields BEFORE starting services
        self._setup_ctrl_handler()

        # 2. Apply full shield: stealth name disguise + DACL anti-kill
        shield_result = apply_all_shields()
        if shield_result["dacl_ok"]:
            print("[SHIELD] DACL anti-kill protection active.")
        print("[SHIELD] Process stealth disguise applied.")

        # 3. Enable boot autostart persistence (Task Scheduler, HKCU Registry, Startup folder)
        try:
            enable_autostart()
            print("[SERVICE] Boot autostart persistence confirmed.")
        except Exception as e:
            print(f"[WARNING] Could not configure autostart: {e}")

        # 4. Start mutual guardian supervisor process
        self._start_guardian_supervisor()

        # 5. Create single hidden root Tk window on main thread
        self.root = tk.Tk()
        self.root.withdraw()

        # 6. Start monitoring thread & background services
        self.start_background_services()

        # 7. Build System Tray Icon menu and run pystray in daemon thread
        menu = (
            item("🛡 Protection: Permanently Active", lambda: None, enabled=False),
            item("⚙ Open Settings / Admin Panel", lambda: self.show_admin()),
        )

        icon_img = create_tray_icon()
        self.tray_icon = pystray.Icon(
            "adult_blocker",
            icon_img,
            "Adult Content Blocker — Permanent Protection Active",
            menu=menu
        )

        t_tray = threading.Thread(target=self.tray_icon.run, daemon=True)
        t_tray.start()

        print("[SERVICE] Running (Tk event loop on main thread, pystray in background thread).")
        self.root.mainloop()


_SINGLE_INSTANCE_MUTEX = None

def enforce_single_instance():
    """Ensure only one instance of the application runs per user session."""
    global _SINGLE_INSTANCE_MUTEX
    try:
        import win32event
        import win32api
        import winerror
        win32api.SetLastError(0)
        mutex_name = "Local\\AdultContentBlocker_SingleInstance_Mutex"
        _SINGLE_INSTANCE_MUTEX = win32event.CreateMutex(None, True, mutex_name)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            sys.exit(0)
    except Exception:
        pass


if __name__ == "__main__":
    enforce_single_instance()
    try:
        app = AdultBlockerApp()
        app.run()
    except Exception as e:
        import traceback
        crash_log = os.path.join(get_base_dir(), "crash.log")
        try:
            with open(crash_log, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass







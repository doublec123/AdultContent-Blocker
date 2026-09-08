# guardian.py — Mutual Watchdog & Self-Healing Process
# Monitors the main Adult Content Blocker process and restarts it instantly if terminated.
# Applies DACL kernel anti-kill protection and stealth name disguise.

import os
import sys
import time
import subprocess

class NullWriter:
    def write(self, s):
        pass
    def flush(self):
        pass

# Ensure print() and stderr writes never crash when running under windowless pythonw.exe or PyInstaller --noconsole
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
from process_shield import apply_all_shields
from config import get_setting

_WIN32_AVAILABLE = False
try:
    import win32api
    import win32con
    import win32event
    import win32process
    import winerror
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False


_GUARDIAN_MUTEX = None

def enforce_single_guardian():
    """Ensure only one instance of the guardian runs per user session."""
    global _GUARDIAN_MUTEX
    if not _WIN32_AVAILABLE:
        return
    try:
        win32api.SetLastError(0)
        mutex_name = "Local\\AdultContentBlocker_Guardian_Mutex"
        _GUARDIAN_MUTEX = win32event.CreateMutex(None, True, mutex_name)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            sys.exit(0)
    except Exception:
        pass


def get_base_dir() -> str:
    """Get root directory of the application."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_blocker_executable_or_script() -> list[str]:
    """
    Returns the launch command list for the blocker.
    Prefers standalone .exe if compiled, else uses pythonw.exe with blocker.py.
    """
    base_dir = get_base_dir()
    exe_path = os.path.join(base_dir, "WindowsSecurityShield.exe")
    if os.path.exists(exe_path):
        return [exe_path]
    
    script_path = os.path.join(base_dir, "blocker.py")
    python_dir = os.path.dirname(sys.executable)
    pythonw_path = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw_path):
        pythonw_path = sys.executable
    return [pythonw_path, script_path]


def launch_blocker() -> subprocess.Popen:
    """Launch the main blocker process in detached background mode."""
    cmd = get_blocker_executable_or_script()
    base_dir = get_base_dir()
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=base_dir,
            creationflags=creationflags,
            close_fds=True
        )
        return proc
    except Exception as e:
        print(f"[GUARDIAN] Error spawning blocker: {e}")
        return None


def is_pid_alive(pid: int) -> bool:
    """Check if process ID is currently running."""
    if not _WIN32_AVAILABLE or pid <= 0:
        return False
    try:
        h = win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid)
        if h:
            res = win32event.WaitForSingleObject(h, 0)
            win32api.CloseHandle(h)
            return res == win32con.WAIT_TIMEOUT
    except Exception:
        return False
    return False


def run_guardian(target_pid: int = 0):
    """Main guardian loop: watches target PID and relaunches blocker if dead."""
    enforce_single_guardian()
    apply_all_shields()

    current_target_pid = target_pid

    print(f"[GUARDIAN] Guardian active. Monitoring blocker (Initial PID: {current_target_pid})...")

    while True:
        try:
            if current_target_pid <= 0 or not is_pid_alive(current_target_pid):
                print(f"[GUARDIAN] Blocker (PID {current_target_pid}) is NOT running! Spawning immediately...")
                proc = launch_blocker()
                if proc:
                    current_target_pid = proc.pid
                    print(f"[GUARDIAN] Blocker revived with new PID: {current_target_pid}")
                time.sleep(1)
            else:
                # Target is alive; wait and re-verify
                if _WIN32_AVAILABLE and current_target_pid > 0:
                    try:
                        h = win32api.OpenProcess(win32con.SYNCHRONIZE, False, current_target_pid)
                        if h:
                            # Wait up to 500ms for process state change
                            res = win32event.WaitForSingleObject(h, 500)
                            win32api.CloseHandle(h)
                            if res == win32con.WAIT_OBJECT_0:
                                # Process just died!
                                print(f"[GUARDIAN] Target PID {current_target_pid} terminated. Immediate respawn triggered.")
                                current_target_pid = 0
                                continue
                    except Exception:
                        pass
                time.sleep(0.3)
        except Exception as e:
            time.sleep(0.5)


if __name__ == "__main__":
    target_pid = 0
    # Safe argument parsing that never crashes if streams or args are missing
    try:
        for i, arg in enumerate(sys.argv):
            if arg == "--target-pid" and i + 1 < len(sys.argv):
                target_pid = int(sys.argv[i + 1])
                break
    except Exception:
        target_pid = 0

    run_guardian(target_pid)

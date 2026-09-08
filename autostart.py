# autostart.py — Multi-tier Windows Boot Autostart Manager
# Uses Task Scheduler (elevated), HKCU Registry Run Key, and Startup Folder for 100% boot reliability.

import os
import sys
import subprocess
import winreg

TASK_NAME = "AdultContentBlocker"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_base_dir() -> str:
    """Get absolute path to application root directory, handling PyInstaller frozen executables."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_vbs_path() -> str:
    """Get absolute path to run_hidden.vbs launcher."""
    return os.path.join(get_base_dir(), "run_hidden.vbs")


def get_startup_vbs_path() -> str:
    """Get absolute path to startup folder shortcut script."""
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup", "AdultContentBlocker.vbs")


def get_launch_target() -> tuple[str, str]:
    """
    Determine the best launch target command and arguments.
    Prefers standalone compiled .exe if present; falls back to run_hidden.vbs.
    """
    base_dir = get_base_dir()
    exe_path = os.path.join(base_dir, "WindowsSecurityShield.exe")
    if os.path.exists(exe_path):
        return exe_path, f'"{exe_path}"'
    
    vbs_path = os.path.join(base_dir, "run_hidden.vbs")
    return "wscript.exe", f'wscript.exe "{vbs_path}"'


def enable_autostart() -> bool:
    """
    Enable autostart across Windows boot mechanisms:
    1. Task Scheduler (runs elevated silently at logon)
    2. HKCU Registry Run key (user logon autostart)
    3. Startup Folder script fallback
    """
    base_dir = get_base_dir()
    exe_path = os.path.join(base_dir, "WindowsSecurityShield.exe")
    use_exe = os.path.exists(exe_path)
    vbs_path = os.path.join(base_dir, "run_hidden.vbs")

    success = False

    # 1. Try Windows Task Scheduler with Highest Privileges
    try:
        if use_exe:
            target_exec = exe_path
            target_args = ""
        else:
            target_exec = "wscript.exe"
            target_args = f'"{vbs_path}"'

        ps_script = f'''
        $action = New-ScheduledTaskAction -Execute '{target_exec}' {f"-Argument '{target_args}'" if target_args else ""}
        $trigger = New-ScheduledTaskTrigger -AtLogOn
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\\$env:USERNAME" -RunLevel Highest
        Register-ScheduledTask -TaskName "{TASK_NAME}" -Action $action -Trigger $trigger -Principal $principal -Force
        '''
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
        if res.returncode == 0:
            success = True
    except Exception:
        pass

    # 2. Add HKCU Registry Run key (always works for current user)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        if use_exe:
            reg_val = f'"{exe_path}"'
        else:
            reg_val = f'wscript.exe "{vbs_path}"'
        winreg.SetValueEx(key, TASK_NAME, 0, winreg.REG_SZ, reg_val)
        winreg.CloseKey(key)
        success = True
    except Exception:
        pass

    # 3. Create Startup folder launcher script
    try:
        startup_file = get_startup_vbs_path()
        os.makedirs(os.path.dirname(startup_file), exist_ok=True)
        with open(startup_file, "w", encoding="utf-8") as f:
            f.write('Set WshShell = CreateObject("WScript.Shell")\n')
            if use_exe:
                f.write(f'WshShell.Run """{exe_path}""", 0, False\n')
            else:
                f.write(f'WshShell.Run "wscript.exe """ & "{vbs_path}" & """", 0, False\n')
        success = True
    except Exception:
        pass

    return success


def disable_autostart() -> bool:
    """Remove application from all Windows autostart entries."""
    # 1. Remove Task Scheduler task
    try:
        cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
        subprocess.run(cmd, capture_output=True, text=True)
    except Exception:
        pass

    # 2. Remove HKCU Registry Run key value
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        try:
            winreg.DeleteValue(key, TASK_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass

    # 3. Remove Startup Folder script
    try:
        startup_file = get_startup_vbs_path()
        if os.path.exists(startup_file):
            os.remove(startup_file)
    except Exception:
        pass

    return True


def is_autostart_enabled() -> bool:
    """Check if any autostart mechanism is configured."""
    # 1. Check Task Scheduler
    try:
        cmd = f'schtasks /query /tn "{TASK_NAME}"'
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if res.returncode == 0:
            return True
    except Exception:
        pass

    # 2. Check HKCU Registry Run key
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, TASK_NAME)
            if val:
                winreg.CloseKey(key)
                return True
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass

    # 3. Check Startup Folder file
    try:
        if os.path.exists(get_startup_vbs_path()):
            return True
    except Exception:
        pass

    return False


if __name__ == "__main__":
    print("[AUTOSTART] Enabling persistence for Adult Content Blocker...")
    res = enable_autostart()
    print(f"[AUTOSTART] Enabled: {res}")
    print(f"[AUTOSTART] Verified Status: {is_autostart_enabled()}")

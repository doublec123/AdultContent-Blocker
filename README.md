# 🛡 Adult Content Blocker for Windows

A robust, tamper-resistant background content filtering application for Windows that blocks adult and pornographic content across all browsers (Chrome, Edge, Firefox, Opera, etc.) and defends itself against termination.

---

## 🌟 Key Features

1. **Task Manager Remains 100% Fully Enabled**
   - No registry policies (`DisableTaskMgr`) or restrictions are placed on Task Manager. Task Manager opens and behaves normally for all system diagnostic needs.

2. **Process Stealth & Disguise**
   - The blocker process is disguised in memory using legitimate Windows system service display names (e.g. `Windows Security Health Service`, `Microsoft Defender Core Service`, etc.).
   - It does NOT appear under recognizable or suspicious names in Task Manager.

3. **Kernel DACL Anti-Kill Process Shield**
   - Modifies the process's Windows NT security descriptor (DACL) to explicitly deny `PROCESS_TERMINATE`, `PROCESS_SUSPEND_RESUME`, and related access rights.
   - When someone clicks **"End task"** in Task Manager or runs `taskkill /f`, the Windows kernel immediately rejects the request with **`Access is denied (Error 5)`** silently.

4. **Mutual Guardian Watchdog (Instant Self-Healing)**
   - Runs a secondary background supervisor (`guardian.py` / `WindowsSecurityGuardian.exe`).
   - The blocker and guardian monitor each other continuously. If either process is terminated, the survivor immediately revives it in under 500ms.

5. **Permanent Background Protection**
   - There is no exit button or stop dialog in the system tray menu to eliminate bypass temptations.

6. **DNS Hosts File Blocking (3000+ Domains)**
   - Automatically maps adult website domains to `0.0.0.0` in `C:\Windows\System32\drivers\etc\hosts`.
   - Flushes Windows DNS cache automatically on launch.

7. **Live Browser Tab Keyword Scanner**
   - Continuously scans open browser window titles every 500ms for 150+ adult keywords and domain patterns across all major browsers.

8. **Fullscreen Block Screen**
   - When adult content is detected, a non-dismissable fullscreen warning overlay appears with a single **"Close & Go Back"** action to close the browser tab.

---

## 🛡 How the Stealth & Anti-Termination Protection Works

| Action / Attempt | What Happens |
|---|---|
| Opening Task Manager | Task Manager opens normally — no blocking or registry disable policies. |
| Looking for the Blocker | The process runs disguised under legitimate Windows background service names. |
| Clicking "End Task" in Task Manager | Windows kernel immediately returns **Access is Denied** (Error 5) silently — the process cannot be killed. |
| Termination from Console (`taskkill`) | Fails with `ERROR: Access is denied`. |
| Process somehow closed / killed | The Mutual Guardian Watchdog revives the blocker in <500ms. |
| Trying to Exit from System Tray | The tray icon runs permanently without an exit/stop button. |

---

## 🚀 How to Install & Run

### Option 1: Right-Click Setup (Recommended)
1. Right-click `install.bat` and select **Run as administrator**.
2. The script will install all dependencies (`pywin32`, `pystray`, `pillow`, `psutil`, `pyinstaller`) and start protection with kernel anti-kill shields.

### Option 2: Compile to Standalone Executable
1. Double-click `build_exe.bat` to compile `WindowsSecurityShield.exe` and `WindowsSecurityGuardian.exe`.
2. Run `install.bat` (as Administrator) to register autostart for the compiled binaries.

### Option 3: Command Line
```cmd
# 1. Install dependencies
pip install pywin32 pystray pillow psutil pyinstaller

# 2. Run application (Run Command Prompt / PowerShell as Admin)
python blocker.py
```

---

## 📁 File Structure

- `blocker.py`: Main entry point, DACL protection, system tray service, stop-code dialog, and guardian supervisor.
- `guardian.py`: Mutual supervisor watchdog process that revives the blocker instantly if closed.
- `process_shield.py`: Windows NT DACL security descriptor manager (blocks termination at kernel level).
- `build_exe.bat`: One-click PyInstaller compiler to generate disguised standalone Windows binaries.
- `block_screen.py`: Fullscreen warning window overlay.
- `title_monitor.py`: Real-time browser window scanner.
- `hosts_manager.py`: Windows hosts file read/write manager.
- `config.py`: Password hashing and application options.
- `blocklist.py`: Adult domains (3,000+) and explicit keyword lists.
- `admin_panel.py`: Control panel GUI.
- `install.bat`: One-click setup batch file.
- `run_hidden.vbs`: Silent windowless background launcher.

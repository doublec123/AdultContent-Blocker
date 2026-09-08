@echo off
TITLE Adult Content Blocker Installer
COLOR 0A
cls

:: Ensure working directory is the script folder (crucial when running as administrator)
cd /d "%~dp0"

echo ========================================================
echo       Adult Content Blocker — Windows Setup
echo ========================================================
echo.

:: Check for Administrator Privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running with Administrator Privileges.
) else (
    echo [WARNING] Not running as Administrator.
    echo Please right-click this installer and select "Run as Administrator"
    echo for full DNS hosts-level and kernel DACL protection.
    echo.
    pause
)

echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo [2/3] Installing required Python packages (pywin32, pystray, pillow, psutil, pyinstaller)...
python -m pip install --upgrade pip --no-warn-script-location
python -m pip install --no-warn-script-location pywin32 pystray pillow psutil pyinstaller

:: Run pywin32 post install setup if available
if exist "%APPDATA%\Python\Python310\Scripts\pywin32_postinstall.py" (
    python "%APPDATA%\Python\Python310\Scripts\pywin32_postinstall.py" -install >nul 2>&1
)

echo.
echo [3/3] Configuring boot autostart & launching Adult Content Blocker...
echo.
echo ========================================================
echo   Default Admin Password: admin123
echo   Protection Status: KERNEL ANTI-KILL & GUARDIAN ACTIVE
echo ========================================================
echo.

:: Register Task Scheduler elevated autostart task and registry key
python "%~dp0autostart.py"

:: Launch silently in background using VBS runner
wscript.exe "%~dp0run_hidden.vbs"

echo Protection started in background with Kernel Anti-Kill Shields!
timeout /t 3 >nul
exit

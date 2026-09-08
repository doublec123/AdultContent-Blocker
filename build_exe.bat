@echo off
TITLE Build Adult Content Blocker Executables
COLOR 0B
cls

cd /d "%~dp0"

echo ========================================================
echo   Compiling Adult Content Blocker into Native Windows Executables
echo   (Disguises process and removes 'Python' from Task Manager)
echo ========================================================
echo.

echo [1/3] Ensuring PyInstaller is installed...
python -m pip install --upgrade pyinstaller --no-warn-script-location

echo.
echo [2/3] Compiling Main Blocker (WindowsSecurityShield.exe)...
python -m PyInstaller --noconsole --onefile --name "WindowsSecurityShield" --distpath "%~dp0." --workpath "%~dp0build" --specpath "%~dp0build" --clean blocker.py

echo.
echo [3/3] Compiling Guardian Watchdog (WindowsSecurityGuardian.exe)...
python -m PyInstaller --noconsole --onefile --name "WindowsSecurityGuardian" --distpath "%~dp0." --workpath "%~dp0build" --specpath "%~dp0build" --clean guardian.py

echo.
echo ========================================================
echo   Compilation Complete!
echo   Output:
echo   - WindowsSecurityShield.exe
echo   - WindowsSecurityGuardian.exe
echo ========================================================
echo.
pause

@echo off
cd /d "%~dp0\.."
py -3.12 scripts\build_windows.py
echo.
pause

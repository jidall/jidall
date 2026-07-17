@echo off
cd /d "%~dp0"
echo [1] Entrou no BAT
echo [1] Entrou no BAT > build_windows.log
echo [2] Chamou Python
echo [2] Chamou Python >> build_windows.log
py -3.12 scripts\build_windows.py
echo [BAT] Python terminou; consulte build_windows.log para o resultado completo.
echo [BAT] Python terminou; consulte build_windows.log para o resultado completo. >> build_windows.log
echo.
pause

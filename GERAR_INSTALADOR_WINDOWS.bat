@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo   Assistente de Provas - Gerador de Instalador Windows
echo ============================================================
echo.

set "BUILD_SCRIPT=%~dp0scripts\build_windows.ps1"
set "LOG_FILE=%~dp0build_installer.log"

if not exist "%BUILD_SCRIPT%" (
  echo [ERRO] Script de build nao encontrado:
  echo "%BUILD_SCRIPT%"
  pause
  exit /b 1
)

echo O processo pode demorar alguns minutos.
echo Um registro sera salvo em:
echo "%LOG_FILE%"
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%BUILD_SCRIPT%" -LogFile "%LOG_FILE%"
set "BUILD_EXIT=%ERRORLEVEL%"

echo.
if not "%BUILD_EXIT%"=="0" (
  echo [ERRO] O build nao foi concluido.
  echo Consulte o arquivo:
  echo "%LOG_FILE%"
  echo.
  pause
  exit /b %BUILD_EXIT%
)

echo [SUCESSO] O Assistente de Provas e o instalador foram gerados.
echo.
pause
exit /b 0

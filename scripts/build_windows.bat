@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0.."

set "ROOT_BUILD=%CD%\GERAR_INSTALADOR_WINDOWS.bat"

if not exist "%ROOT_BUILD%" (
  echo [ERRO] Arquivo principal de build nao encontrado:
  echo "%ROOT_BUILD%"
  pause
  exit /b 1
)

call "%ROOT_BUILD%"
exit /b %ERRORLEVEL%

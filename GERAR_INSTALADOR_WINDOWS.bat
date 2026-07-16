@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%CD%"
echo === Assistente de Provas - Gerador de Instalador Windows ===
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 nao foi encontrado. Instale Python 3.12 e execute novamente.
  pause
  exit /b 1
)
if not exist ".venv" (
  echo Criando ambiente virtual...
  py -3.12 -m venv ".venv"
  if errorlevel 1 goto :erro
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :erro
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :erro
python -m pip install -e .
if errorlevel 1 goto :erro
pyinstaller --noconfirm "Assistente de Provas.spec"
if errorlevel 1 goto :erro
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo Inno Setup nao foi encontrado. Instale Inno Setup 6 para gerar o instalador.
  echo Executavel gerado em: "!ROOT!\dist\Assistente de Provas\Assistente de Provas.exe"
  pause
  exit /b 1
)
"!ISCC!" "installer\assistente_de_provas.iss"
if errorlevel 1 goto :erro
echo.
echo Executavel: "!ROOT!\dist\Assistente de Provas\Assistente de Provas.exe"
echo Instalador: "!ROOT!\installer\Output\Assistente_de_Provas_Setup.exe"
echo Concluido.
pause
exit /b 0
:erro
echo Ocorreu uma falha no build. Verifique as mensagens acima.
echo Pasta do projeto: "!ROOT!"
pause
exit /b 1

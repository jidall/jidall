param(
    [string]$LogFile = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

if ([string]::IsNullOrWhiteSpace($LogFile)) {
    $LogFile = Join-Path $root "build_installer.log"
}

$logDirectory = Split-Path -Parent $LogFile
if ($logDirectory -and -not (Test-Path $logDirectory)) {
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
}

Start-Transcript -Path $LogFile -Force | Out-Null

function Stop-Build {
    param([string]$Message)
    Write-Host ""
    Write-Host "[ERRO] $Message" -ForegroundColor Red
    throw $Message
}

try {
    Write-Host "=== Assistente de Provas - Build Windows ==="
    Write-Host "Projeto: $root"
    Write-Host "Log: $LogFile"

    $pythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if (-not $pythonLauncher) {
        Stop-Build "O Python Launcher (py.exe) nao foi encontrado. Instale o Python 3.12 para Windows."
    }

    & py -3.12 --version
    if ($LASTEXITCODE -ne 0) {
        Stop-Build "O Python 3.12 nao foi encontrado."
    }

    $venvDir = Join-Path $root ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"
    $venvPyInstaller = Join-Path $venvDir "Scripts\pyinstaller.exe"

    if (-not (Test-Path $venvPython)) {
        Write-Host "Criando ambiente virtual..."
        & py -3.12 -m venv $venvDir
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
            Stop-Build "Falha ao criar o ambiente virtual."
        }
    }

    Write-Host "Atualizando pip..."
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Stop-Build "Falha ao atualizar o pip." }

    Write-Host "Instalando dependencias de build..."
    & $venvPython -m pip install -r (Join-Path $root "requirements-build.txt")
    if ($LASTEXITCODE -ne 0) { Stop-Build "Falha ao instalar requirements-build.txt." }

    Write-Host "Instalando o projeto..."
    & $venvPython -m pip install -e $root
    if ($LASTEXITCODE -ne 0) { Stop-Build "Falha ao instalar o projeto em modo editavel." }

    $specFile = Join-Path $root "Assistente de Provas.spec"
    if (-not (Test-Path $specFile)) {
        Stop-Build "Arquivo spec nao encontrado: $specFile"
    }

    Write-Host "Limpando saidas antigas..."
    $buildDir = Join-Path $root "build"
    $distDir = Join-Path $root "dist"
    $installerOutputDir = Join-Path $root "installer\Output"
    Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $distDir -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $installerOutputDir -ErrorAction SilentlyContinue

    Write-Host "Gerando executavel com PyInstaller..."
    & $venvPyInstaller --noconfirm --clean $specFile
    if ($LASTEXITCODE -ne 0) { Stop-Build "O PyInstaller retornou erro." }

    $appExe = Join-Path $root "dist\Assistente de Provas\Assistente de Provas.exe"
    if (-not (Test-Path $appExe)) {
        Stop-Build "Executavel nao encontrado apos o PyInstaller: $appExe"
    }
    Write-Host "[OK] Executavel gerado: $appExe" -ForegroundColor Green

    $isccCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    ) | Where-Object { $_ -and (Test-Path $_) }

    $iscc = $isccCandidates | Select-Object -First 1
    if (-not $iscc) {
        Stop-Build "Inno Setup 6 nao encontrado. Instale-o e execute novamente. O executavel ja foi criado em: $appExe"
    }

    $issFile = Join-Path $root "installer\assistente_de_provas.iss"
    if (-not (Test-Path $issFile)) {
        Stop-Build "Arquivo do Inno Setup nao encontrado: $issFile"
    }

    Write-Host "Gerando instalador com Inno Setup..."
    & $iscc $issFile
    if ($LASTEXITCODE -ne 0) { Stop-Build "O Inno Setup retornou erro." }

    $installerExe = Join-Path $root "installer\Output\Assistente_de_Provas_Setup.exe"
    if (-not (Test-Path $installerExe)) {
        Stop-Build "Instalador nao encontrado apos o Inno Setup: $installerExe"
    }

    Write-Host ""
    Write-Host "[SUCESSO] Build concluido." -ForegroundColor Green
    Write-Host "Executavel: $appExe"
    Write-Host "Instalador: $installerExe"
    Write-Host "Log: $LogFile"
    exit 0
}
catch {
    Write-Host ""
    Write-Host "Falha: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Consulte o log: $LogFile"
    exit 1
}
finally {
    try { Stop-Transcript | Out-Null } catch { }
}

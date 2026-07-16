$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
if (-not (Test-Path ".venv")) {
  py -3.12 -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
& .\.venv\Scripts\python.exe -m pip install -e .
& .\.venv\Scripts\pyinstaller.exe --noconfirm "Assistente de Provas.spec"
$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
  $candidates = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "${env:ProgramFiles}\Inno Setup 6\ISCC.exe")
  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) { $iscc = Get-Item $candidate; break }
  }
}
if ($iscc) {
  & $iscc.FullName "installer\assistente_de_provas.iss"
  Write-Host "Executavel: $root\dist\Assistente de Provas\Assistente de Provas.exe"
  Write-Host "Instalador: $root\installer\Output\Assistente_de_Provas_Setup.exe"
} else {
  Write-Warning "Inno Setup (ISCC.exe) não encontrado. Executável gerado; instale Inno Setup 6 para gerar Assistente_de_Provas_Setup.exe."
  Write-Host "Executavel: $root\dist\Assistente de Provas\Assistente de Provas.exe"
}

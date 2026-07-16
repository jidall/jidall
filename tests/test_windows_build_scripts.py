from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_batch_delegates_to_powershell_with_quoted_paths() -> None:
    content = (ROOT / "GERAR_INSTALADOR_WINDOWS.bat").read_text(encoding="utf-8")
    assert 'set "BUILD_SCRIPT=' in content
    assert 'set "LOG_FILE=' in content
    assert 'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%BUILD_SCRIPT%" -LogFile "%LOG_FILE%"' in content


def test_powershell_build_checks_expected_artifacts() -> None:
    content = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    assert 'dist\\Assistente de Provas\\Assistente de Provas.exe' in content
    assert 'installer\\Output\\Assistente_de_Provas_Setup.exe' in content
    assert 'Start-Transcript' in content
    assert 'Stop-Transcript' in content


def test_inno_setup_quotes_source_with_spaces() -> None:
    content = (ROOT / "installer" / "assistente_de_provas.iss").read_text(encoding="utf-8")
    assert 'Source: "..\\dist\\Assistente de Provas\\*"' in content
    assert 'Filename: "{app}\\{#MyAppExeName}"' in content

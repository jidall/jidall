from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_windows.py"
spec = importlib.util.spec_from_file_location("build_windows", SCRIPT)
assert spec and spec.loader
build_windows = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = build_windows
spec.loader.exec_module(build_windows)


def test_build_paths_preserve_project_root(tmp_path):
    paths = build_windows.BuildPaths(tmp_path / "jidall-main (1)")

    assert paths.log_file == paths.root / "build_windows.log"
    assert paths.executable.name == "Assistente de Provas.exe"
    assert paths.installer.name == "Assistente_de_Provas_Setup.exe"


def test_find_inno_setup_uses_program_files(monkeypatch, tmp_path):
    inno_root = tmp_path / "Program Files (x86)" / "Inno Setup 6"
    inno_root.mkdir(parents=True)
    iscc = inno_root / "ISCC.exe"
    iscc.touch()
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "Program Files (x86)"))
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.setattr(build_windows.shutil, "which", lambda _: None)

    builder = build_windows.WindowsBuilder(build_windows.BuildPaths(tmp_path), logging.getLogger("test-build"))

    assert builder.find_inno_setup() == iscc


def test_bat_launchers_only_delegate_to_python():
    repository = SCRIPT.parents[1]
    root_launcher = (repository / "GERAR_INSTALADOR_WINDOWS.bat").read_text(encoding="utf-8").splitlines()
    helper_launcher = (repository / "scripts" / "build_windows.bat").read_text(encoding="utf-8").splitlines()

    assert root_launcher == [
        "@echo off",
        'cd /d "%~dp0"',
        "py -3.12 scripts\\build_windows.py",
        "echo.",
        "pause",
    ]
    assert helper_launcher == [
        "@echo off",
        'cd /d "%~dp0\\.."',
        "py -3.12 scripts\\build_windows.py",
        "echo.",
        "pause",
    ]


def test_run_command_uses_argument_list_check_true_and_project_cwd(monkeypatch, tmp_path):
    calls: list[tuple[list[str], dict]] = []

    def successful_run(command, **kwargs):
        calls.append((command, kwargs))
        return build_windows.subprocess.CompletedProcess(command, 0, "processo concluído")

    monkeypatch.setattr(build_windows.subprocess, "run", successful_run)
    logger = logging.getLogger("test-build-command")
    builder = build_windows.WindowsBuilder(build_windows.BuildPaths(tmp_path / "diretório (1)"), logger)

    builder.run_command(["python.exe", "-m", "PyInstaller", "arquivo.spec"], description="Teste")

    command, kwargs = calls[0]
    assert command == ["python.exe", "-m", "PyInstaller", "arquivo.spec"]
    assert kwargs["cwd"] == builder.paths.root
    assert kwargs["check"] is True


def test_run_command_logs_complete_output_when_a_command_fails(monkeypatch, caplog, tmp_path):
    def failed_run(command, **kwargs):
        raise build_windows.subprocess.CalledProcessError(9, command, output="erro detalhado\nlinha final")

    monkeypatch.setattr(build_windows.subprocess, "run", failed_run)
    logger = logging.getLogger("test-build-command-failure")
    builder = build_windows.WindowsBuilder(build_windows.BuildPaths(tmp_path), logger)

    with caplog.at_level(logging.INFO):
        try:
            builder.run_command(["iscc.exe", "arquivo.iss"], description="Gerando instalador")
        except build_windows.BuildFailure as error:
            assert "código de saída 9" in str(error)
        else:
            raise AssertionError("BuildFailure era esperado")

    assert "erro detalhado" in caplog.text
    assert "linha final" in caplog.text

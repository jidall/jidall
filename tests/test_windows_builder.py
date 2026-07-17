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
    for launcher in (repository / "GERAR_INSTALADOR_WINDOWS.bat", repository / "scripts" / "build_windows.bat"):
        content = launcher.read_text(encoding="utf-8").lower()
        assert "build_windows.py" in content
        assert "powershell" not in content

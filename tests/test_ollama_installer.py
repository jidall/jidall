from __future__ import annotations

import subprocess
from pathlib import Path

from ai.providers import ProviderStatus
from services.ollama_installer import OLLAMA_INSTALL_SCRIPT_URL, OllamaInstallerService


class FakeProvider:
    def __init__(self, status):
        self.status = status

    def test_connection(self):
        return self.status


class FakeRunner:
    def __init__(self):
        self.commands = []

    def run(self, command, timeout=None):
        self.commands.append((command, timeout))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")


def test_inspect_reports_missing_ollama(monkeypatch):
    monkeypatch.setattr("services.ollama_installer.shutil.which", lambda name: None)
    monkeypatch.setattr(Path, "exists", lambda self: False)
    service = OllamaInstallerService(provider=FakeProvider(ProviderStatus(False, "Serviço não iniciado", "offline", [])), runner=FakeRunner())
    state = service.inspect()
    assert not state.installed
    assert state.executable_path is None


def test_inspect_reports_installed_without_models(monkeypatch):
    monkeypatch.setattr("services.ollama_installer.shutil.which", lambda name: "C:/Ollama/ollama.exe")
    service = OllamaInstallerService(provider=FakeProvider(ProviderStatus(True, "Modelo não instalado", "sem modelos", [])), runner=FakeRunner())
    state = service.inspect()
    assert state.installed
    assert not state.has_models


def test_install_ollama_uses_official_script(monkeypatch):
    runner = FakeRunner()
    service = OllamaInstallerService(provider=FakeProvider(ProviderStatus(False, "offline", "", [])), runner=runner)
    result = service.install_ollama()
    assert result.returncode == 0
    command = runner.commands[0][0]
    assert "powershell" in command[0].lower()
    assert OLLAMA_INSTALL_SCRIPT_URL in command[-1]


def test_install_model_uses_ollama_pull(monkeypatch):
    monkeypatch.setattr("services.ollama_installer.shutil.which", lambda name: "ollama")
    runner = FakeRunner()
    service = OllamaInstallerService(provider=FakeProvider(ProviderStatus(True, "Conectado", "", ["llama3.1"])), runner=runner)
    service.install_model("llama3.1")
    assert runner.commands[0][0] == ["ollama", "pull", "llama3.1"]


def test_recommended_models_are_available():
    assert "llama3.1" in OllamaInstallerService(provider=FakeProvider(ProviderStatus(False, "", "", [])), runner=FakeRunner()).recommended_models()

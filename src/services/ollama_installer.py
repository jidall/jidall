from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ai.ollama_provider import OllamaProvider
from ai.providers import ProviderStatus

OLLAMA_INSTALL_SCRIPT_URL = "https://ollama.com/install.ps1"
RECOMMENDED_MODELS = ("llama3.1", "qwen2.5:7b", "gemma2:2b")


class CommandRunner(Protocol):
    def run(self, command: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(self, command: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)


@dataclass(frozen=True)
class OllamaInstallationState:
    executable_path: str | None
    installed: bool
    service_status: ProviderStatus
    models: list[str]

    @property
    def has_models(self) -> bool:
        return bool(self.models)


class OllamaInstallerService:
    def __init__(self, provider: OllamaProvider | None = None, runner: CommandRunner | None = None) -> None:
        self.provider = provider or OllamaProvider()
        self.runner = runner or SubprocessRunner()

    def detect_executable(self) -> str | None:
        found = shutil.which("ollama")
        if found:
            return found
        for candidate in self._windows_candidates():
            if candidate.exists():
                return str(candidate)
        return None

    def inspect(self) -> OllamaInstallationState:
        executable = self.detect_executable()
        status = self.provider.test_connection()
        return OllamaInstallationState(executable, executable is not None, status, status.models)

    def install_ollama(self) -> subprocess.CompletedProcess[str]:
        if platform.system().lower() != "windows":
            return self.runner.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"irm {OLLAMA_INSTALL_SCRIPT_URL} | iex"], timeout=1800)
        return self.runner.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"irm {OLLAMA_INSTALL_SCRIPT_URL} | iex"], timeout=1800)

    def install_model(self, model: str) -> subprocess.CompletedProcess[str]:
        executable = self.detect_executable() or "ollama"
        return self.runner.run([executable, "pull", model], timeout=None)

    def recommended_models(self) -> tuple[str, ...]:
        return RECOMMENDED_MODELS

    def _windows_candidates(self) -> list[Path]:
        local_app_data = os.getenv("LOCALAPPDATA")
        program_files = os.getenv("ProgramFiles")
        candidates: list[Path] = []
        if local_app_data:
            candidates.append(Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe")
        if program_files:
            candidates.append(Path(program_files) / "Ollama" / "ollama.exe")
        return candidates

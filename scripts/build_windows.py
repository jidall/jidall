"""Build the Windows executable and Inno Setup installer for Assistente de Provas.

This script deliberately owns the complete build workflow so the .bat launchers
remain safe even when the project directory contains spaces or parentheses.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from dataclasses import dataclass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_NAME = "build_windows.log"


class BuildFailure(RuntimeError):
    """Raised when a required build step fails."""


@dataclass(frozen=True)
class BuildPaths:
    root: Path

    @property
    def log_file(self) -> Path:
        return self.root / LOG_NAME

    @property
    def venv_dir(self) -> Path:
        return self.root / ".venv"

    @property
    def python(self) -> Path:
        return self.venv_dir / "Scripts" / "python.exe"

    @property
    def executable(self) -> Path:
        return self.root / "dist" / "Assistente de Provas" / "Assistente de Provas.exe"

    @property
    def installer(self) -> Path:
        return self.root / "installer" / "Output" / "Assistente_de_Provas_Setup.exe"


def configure_logger(log_file: Path) -> logging.Logger:
    logger = logging.getLogger("assistente_de_provas.windows_build")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="w")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


class WindowsBuilder:
    def __init__(self, paths: BuildPaths, logger: logging.Logger) -> None:
        self.paths = paths
        self.logger = logger

    def run_command(self, command: list[str], *, description: str) -> None:
        self.logger.info("\n%s", description)
        self.logger.info("Comando: %s", subprocess.list2cmdline(command))
        try:
            completed = subprocess.run(
                command,
                cwd=self.paths.root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
        except OSError as error:
            raise BuildFailure(f"Não foi possível iniciar '{command[0]}': {error}") from error

        if completed.stdout:
            for line in completed.stdout.rstrip().splitlines():
                self.logger.info("  %s", line)
        if completed.returncode:
            raise BuildFailure(f"{description} falhou com código de saída {completed.returncode}.")

    def ensure_virtual_environment(self) -> None:
        if self.paths.python.exists():
            self.logger.info("Ambiente virtual existente: %s", self.paths.venv_dir)
            return
        self.run_command(
            [sys.executable, "-m", "venv", str(self.paths.venv_dir)],
            description="Criando ambiente virtual Python 3.12",
        )
        if not self.paths.python.exists():
            raise BuildFailure("O ambiente virtual foi criado, mas python.exe não foi encontrado.")

    def install_dependencies(self) -> None:
        python = str(self.paths.python)
        self.run_command([python, "-m", "pip", "install", "--upgrade", "pip"], description="Atualizando pip")
        self.run_command(
            [python, "-m", "pip", "install", "-r", "requirements-build.txt"],
            description="Instalando dependências de build",
        )
        self.run_command([python, "-m", "pip", "install", "-e", "."], description="Instalando o projeto")

    def build_executable(self) -> None:
        self.run_command(
            [str(self.paths.python), "-m", "PyInstaller", "--noconfirm", "Assistente de Provas.spec"],
            description="Gerando Assistente de Provas.exe",
        )
        if not self.paths.executable.exists():
            raise BuildFailure(f"O executável esperado não foi gerado: {self.paths.executable}")

    def find_inno_setup(self) -> Path | None:
        executable = shutil.which("ISCC.exe") or shutil.which("iscc")
        if executable:
            return Path(executable)

        program_files = [os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")]
        for base in filter(None, program_files):
            candidate = Path(base) / "Inno Setup 6" / "ISCC.exe"
            if candidate.exists():
                return candidate
        return None

    def build_installer(self) -> None:
        iscc = self.find_inno_setup()
        if iscc is None:
            raise BuildFailure(
                "Inno Setup 6 (ISCC.exe) não foi encontrado. Instale-o e execute este arquivo novamente."
            )
        self.run_command([str(iscc), "installer\\assistente_de_provas.iss"], description="Gerando instalador Windows")
        if not self.paths.installer.exists():
            raise BuildFailure(f"O instalador esperado não foi gerado: {self.paths.installer}")

    def build(self) -> None:
        self.logger.info("=== Assistente de Provas - Gerador de Instalador Windows ===")
        self.logger.info("Pasta do projeto: %s", self.paths.root)
        self.logger.info("Log completo: %s", self.paths.log_file)
        self.logger.info("Python que iniciou o build: %s", sys.executable)
        if sys.version_info[:2] != (3, 12):
            raise BuildFailure("Python 3.12 é obrigatório. Execute GERAR_INSTALADOR_WINDOWS.bat com o Python Launcher instalado.")
        if os.name != "nt":
            raise BuildFailure("Este script deve ser executado no Windows para gerar o executável e o instalador.")

        self.ensure_virtual_environment()
        self.install_dependencies()
        self.build_executable()
        self.build_installer()
        self.logger.info("\nBuild concluído com sucesso.")
        self.logger.info("Executável: %s", self.paths.executable)
        self.logger.info("Instalador: %s", self.paths.installer)


def wait_for_enter() -> None:
    try:
        input("\nPressione ENTER para fechar esta janela...")
    except (EOFError, KeyboardInterrupt):
        pass


def main() -> int:
    paths = BuildPaths(PROJECT_ROOT)
    logger = configure_logger(paths.log_file)
    exit_code = 0
    try:
        WindowsBuilder(paths, logger).build()
    except BuildFailure as error:
        exit_code = 1
        logger.error("\nFALHA NO BUILD: %s", error)
    except Exception:
        exit_code = 1
        logger.exception("\nFALHA INESPERADA NO BUILD")
    finally:
        logger.info("\nConsulte o log completo em: %s", paths.log_file)
        wait_for_enter()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

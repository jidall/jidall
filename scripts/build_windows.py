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
    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def write_log(logger: logging.Logger, level: int, message: str, *args: object) -> None:
    """Write and flush a diagnostic entry before the next build action starts."""
    logger.log(level, message, *args)
    for handler in logger.handlers:
        handler.flush()


class WindowsBuilder:
    def __init__(self, paths: BuildPaths, logger: logging.Logger) -> None:
        self.paths = paths
        self.logger = logger

    def log(self, message: str, *args: object) -> None:
        write_log(self.logger, logging.INFO, message, *args)

    def run_command(self, command: list[str], *, description: str) -> None:
        self.log("\n%s", description)
        self.log("Comando: %s", subprocess.list2cmdline(command))
        try:
            completed = subprocess.run(
                command,
                cwd=self.paths.root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            self._log_command_output(error.stdout)
            raise BuildFailure(f"{description} falhou com código de saída {error.returncode}.") from error
        except OSError as error:
            raise BuildFailure(f"Não foi possível iniciar '{command[0]}': {error}") from error

        self._log_command_output(completed.stdout)

    def _log_command_output(self, output: str | None) -> None:
        if not output:
            return
        for line in output.rstrip().splitlines():
            self.log("  %s", line)

    def ensure_virtual_environment(self) -> None:
        if self.paths.python.exists():
            self.log("Ambiente virtual existente: %s", self.paths.venv_dir)
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
            [
                str(self.paths.python),
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                str(self.paths.root / "Assistente de Provas.spec"),
            ],
            description="Gerando Assistente de Provas.exe",
        )

    def validate_executable(self) -> None:
        if not self.paths.executable.exists():
            raise BuildFailure(f"O executável esperado não foi gerado: {self.paths.executable}")
        self.log("Executável validado: %s", self.paths.executable)

    def find_inno_setup(self) -> Path | None:
        try:
            completed = subprocess.run(
                ["where.exe", "ISCC.exe"],
                cwd=self.paths.root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
            )
        except (subprocess.CalledProcessError, OSError):
            completed = None

        if completed and completed.stdout:
            for line in completed.stdout.splitlines():
                candidate = Path(line.strip())
                if candidate.exists():
                    return candidate

        local_app_data = os.environ.get("LOCALAPPDATA")
        candidates = []
        if local_app_data:
            candidates.append(Path(local_app_data) / "Programs" / "Inno Setup 6" / "ISCC.exe")
        candidates.extend(
            [
                Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
                Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def build_installer(self) -> None:
        self.log("[8] Procurando Inno Setup")
        iscc = self.find_inno_setup()
        if iscc is None:
            raise BuildFailure(
                "Inno Setup 6 (ISCC.exe) não foi encontrado. Instale-o e execute este arquivo novamente."
            )
        self.log("[9] Executando Inno Setup")
        self.run_command(
            [str(iscc), str(self.paths.root / "installer" / "assistente_de_provas.iss")],
            description="Gerando instalador Windows",
        )
        if not self.paths.installer.exists():
            raise BuildFailure(f"O instalador esperado não foi gerado: {self.paths.installer}")
        self.log("Instalador validado: %s", self.paths.installer)

    def build(self) -> None:
        self.log("=== Assistente de Provas - Gerador de Instalador Windows ===")
        self.log("[2] Python iniciou o build")
        self.log("Pasta do projeto: %s", self.paths.root)
        self.log("Log completo: %s", self.paths.log_file)
        self.log("Python que iniciou o build: %s", sys.executable)
        if sys.version_info[:2] != (3, 12):
            raise BuildFailure("Python 3.12 é obrigatório. Execute GERAR_INSTALADOR_WINDOWS.bat com o Python Launcher instalado.")
        if os.name != "nt":
            raise BuildFailure("Este script deve ser executado no Windows para gerar o executável e o instalador.")

        self.log("[3] Criando ou validando venv")
        self.ensure_virtual_environment()
        self.log("[3] Venv disponível")
        self.log("[4] Instalando requirements")
        self.install_dependencies()
        self.log("[4] Requirements instalados")
        self.log("[5] Executando PyInstaller")
        self.build_executable()
        self.log("[6] PyInstaller terminou")
        self.log("[7] Validando EXE")
        self.validate_executable()
        self.build_installer()
        self.log("[10] Build concluído")
        self.log("Executável: %s", self.paths.executable)
        self.log("Instalador: %s", self.paths.installer)


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
        write_log(logger, logging.ERROR, "\nFALHA NO BUILD: %s\n%s", error, traceback.format_exc())
    except Exception:
        exit_code = 1
        write_log(logger, logging.ERROR, "\nFALHA INESPERADA NO BUILD\n%s", traceback.format_exc())
    finally:
        write_log(logger, logging.INFO, "\nConsulte o log completo em: %s", paths.log_file)
        wait_for_enter()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

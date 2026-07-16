from __future__ import annotations

from pathlib import Path
from exporters.word_exporter import WordExporter
from models.assessment import GenerationResult


class Executor:
    """EXECUTOR: exports final deliverables."""

    def __init__(self) -> None:
        self.exporter = WordExporter()

    def export(self, result: GenerationResult, output_dir: Path, output_name: str):
        return self.exporter.export(result, output_dir, output_name)

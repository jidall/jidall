from __future__ import annotations

from pathlib import Path
import re
try:
    import fitz
except ImportError:  # pragma: no cover - exercised only without optional dependency
    fitz = None
from models.assessment import SourceDocument, SourcePage

_AULA_RE = re.compile(r"\bAula\s+(\d+)", re.I)
_THEME_RE = re.compile(r"\b(?:Tema|Unidade|Cap[íi]tulo)\s+\d+[:\-–]?\s*([^\n\r]{0,100})", re.I)


def infer_document_type(path: Path) -> str:
    name = path.name.lower()
    if "slide" in name:
        return "slides"
    if "plano" in name or "ensino" in name:
        return "plano de ensino"
    if "banco" in name or "quest" in name:
        return "banco de questões"
    return "texto da aula"


def infer_aula(text: str, fallback: str | None = None) -> str | None:
    match = _AULA_RE.search(text)
    return f"Aula {match.group(1)}" if match else fallback


def infer_theme(text: str) -> str | None:
    match = _THEME_RE.search(text)
    if not match:
        return None
    title = match.group(0).strip().replace("\n", " ")
    return title[:140]


class PdfReader:
    def read(self, path: Path, document_type: str | None = None) -> SourceDocument:
        document_type = document_type or infer_document_type(path)
        if fitz is None:
            raise RuntimeError("PyMuPDF não está instalado. Instale a dependência PyMuPDF para ler PDFs.")
        pages: list[SourcePage] = []
        current_aula: str | None = None
        current_theme: str | None = None
        with fitz.open(path) as doc:
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                current_aula = infer_aula(text, current_aula)
                current_theme = infer_theme(text) or current_theme
                pages.append(SourcePage(path.name, str(path), index, text, document_type, current_aula, current_theme))
        return SourceDocument(path=path, document_type=document_type, pages=pages)

    def read_many(self, paths: list[Path]) -> list[SourceDocument]:
        return [self.read(path) for path in paths if path.suffix.lower() == ".pdf"]

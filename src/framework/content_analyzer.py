from __future__ import annotations

from dataclasses import dataclass
from models.assessment import SourceDocument, ThemeMap
from services.theme_mapper import ThemeMapper


@dataclass(frozen=True)
class ContentAnalysis:
    theme_map: ThemeMap
    summary: str
    total_pages: int
    total_characters: int


class ContentAnalyzer:
    """CONTENT_ANALYZER: reads extracted document text and produces usable context."""

    def __init__(self) -> None:
        self.mapper = ThemeMapper()

    def analyze(self, documents: list[SourceDocument], aula: str) -> ContentAnalysis:
        theme_map = self.mapper.build(documents, aula)
        total_pages = sum(len(doc.pages) for doc in documents)
        total_characters = sum(len(page.text) for doc in documents for page in doc.pages)
        doc_types = sorted({doc.document_type for doc in documents}) or ["nenhum documento"]
        themes = "; ".join(theme_map.themes[:8])
        summary = (
            f"Foram lidos {len(documents)} documento(s), totalizando {total_pages} página(s) "
            f"e {total_characters} caracteres extraídos. Tipos identificados: {', '.join(doc_types)}. "
            f"Principais conteúdos/temas: {themes or 'não identificados automaticamente'}."
        )
        if theme_map.divergences:
            summary += " Divergências: " + " | ".join(theme_map.divergences)
        return ContentAnalysis(theme_map, summary, total_pages, total_characters)

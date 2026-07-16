from __future__ import annotations

from document_readers.pdf_reader import PdfReader
from models.assessment import SourceDocument


class Engine:
    """ENGINE: coordinates document ingestion for the framework."""

    def __init__(self) -> None:
        self.pdf_reader = PdfReader()

    def read_documents(self, paths) -> list[SourceDocument]:
        return self.pdf_reader.read_many(list(paths))

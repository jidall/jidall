from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ProfileName(str, Enum):
    GRADE_ANTIGA = "Grade Antiga"
    MARCO_REGULATORIO = "Marco Regulatório"


class Operation(str, Enum):
    GERAR_NOVAS = "gerar questões novas"
    REVISAR_EXISTENTES = "revisar questões existentes"
    APENAS_OBJETIVAS = "gerar apenas objetivas"
    APENAS_DISCURSIVAS = "gerar apenas discursivas"
    BANCO_COMPLETO = "gerar banco completo"


@dataclass(frozen=True)
class SourcePage:
    file_name: str
    file_path: str
    page_number: int
    text: str
    document_type: str = "material"
    aula: str | None = None
    theme: str | None = None


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    document_type: str
    pages: list[SourcePage]


@dataclass(frozen=True)
class ThemeMap:
    aula: str
    themes: list[str]
    divergences: list[str]
    page_index: dict[str, list[int]] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceSnippet:
    document_name: str
    document_type: str
    aula: str | None
    theme: str | None
    page_number: int
    text: str
    score: float = 0.0


@dataclass
class Alternative:
    label: str
    text: str
    is_correct: bool
    justification: str


@dataclass
class Question:
    kind: str
    introduction: str
    command: str
    category: str | None = None
    alternatives: list[Alternative] = field(default_factory=list)
    answer: str = ""
    reference: str = ""
    difficulty: str | None = None
    bloom_taxonomy: str | None = None
    competence: str | None = None
    skill: str | None = None
    source_snippets: list[SourceSnippet] = field(default_factory=list)


@dataclass
class GenerationRequest:
    profile: ProfileName
    operation: Operation
    aula: str
    quantity: int
    output_dir: Path
    output_name: str
    files: list[Path]
    only_selected_materials: bool = True


@dataclass
class GenerationResult:
    questions: list[Question]
    audit_messages: list[str]
    theme_map: ThemeMap

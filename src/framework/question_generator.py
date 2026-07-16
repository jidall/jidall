from __future__ import annotations

from ai.question_provider import QuestionProvider
from models.assessment import Question, SourceDocument, SourceSnippet
from profiles.rules import ProfileRules
from framework.content_analyzer import ContentAnalysis


class QuestionGenerator:
    """QUESTION_GENERATOR: delegates generation to the configured provider."""

    def __init__(self, provider: QuestionProvider) -> None:
        self.provider = provider

    def generate(self, documents: list[SourceDocument], analysis: ContentAnalysis, rules: ProfileRules, quantity: int, operation: str, retrieved_context: list[list[SourceSnippet]], only_selected_materials: bool) -> list[Question]:
        return self.provider.generate_questions(
            documents=documents,
            theme_map=analysis.theme_map,
            rules=rules,
            quantity=quantity,
            operation=operation,
            retrieved_context=retrieved_context,
            only_selected_materials=only_selected_materials,
        )

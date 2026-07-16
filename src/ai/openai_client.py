from __future__ import annotations

from ai.openai_provider import OpenAIProvider
from ai.question_provider import AIQuestionProvider, QuestionProvider

OpenAICompatibleProvider = OpenAIProvider

__all__ = ["OpenAIProvider", "OpenAICompatibleProvider", "AIQuestionProvider", "QuestionProvider"]

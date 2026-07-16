from __future__ import annotations

from models.assessment import GenerationRequest, GenerationResult
from ai.question_provider import QuestionProvider
from framework.question_generation_pipeline import QuestionGenerationPipeline
from framework.content_analyzer import ContentAnalysis


class GenerationService:
    def __init__(self, provider: QuestionProvider) -> None:
        self.pipeline = QuestionGenerationPipeline(provider)

    def analyze(self, request: GenerationRequest) -> ContentAnalysis:
        return self.pipeline.analyze_only(request)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        return self.pipeline.run(request)

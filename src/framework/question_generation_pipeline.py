from __future__ import annotations

from ai.question_provider import QuestionProvider
from framework.brain import Brain
from framework.content_analyzer import ContentAnalysis, ContentAnalyzer
from framework.engine import Engine
from framework.question_generator import QuestionGenerator
from models.assessment import GenerationRequest, GenerationResult
from services.rag_retriever import RagRetriever
from validators.question_validator import QuestionValidator


class QuestionGenerationPipeline:
    """QUESTION_GENERATION_PIPELINE: end-to-end framework workflow."""

    def __init__(self, provider: QuestionProvider) -> None:
        self.engine = Engine()
        self.brain = Brain()
        self.analyzer = ContentAnalyzer()
        self.retriever = RagRetriever()
        self.generator = QuestionGenerator(provider)
        self.validator = QuestionValidator()
        self.last_analysis: ContentAnalysis | None = None

    def analyze_only(self, request: GenerationRequest) -> ContentAnalysis:
        documents = self.engine.read_documents(request.files)
        analysis = self.analyzer.analyze(documents, request.aula)
        self.last_analysis = analysis
        return analysis

    def run(self, request: GenerationRequest) -> GenerationResult:
        documents = self.engine.read_documents(request.files)
        document_types = {doc.document_type for doc in documents}
        rules = self.brain.decide_rules(request, document_types)
        analysis = self.analyzer.analyze(documents, request.aula)
        retrieval_plan = self.retriever.build_plan(documents, analysis.theme_map, request.quantity)
        questions = self.generator.generate(documents, analysis, rules, request.quantity, request.operation.value, retrieval_plan.snippets_by_question, request.only_selected_materials)
        audit = self.validator.validate(questions, rules, request.quantity)
        if hasattr(self.generator.provider, "generation_notes"):
            audit.extend(getattr(self.generator.provider, "generation_notes"))
        empty_pages = [f"{page.file_name} p. {page.page_number}" for doc in documents for page in doc.pages if not page.text.strip()]
        if empty_pages:
            audit.append("Páginas sem texto extraível; OCR não executado nesta versão: " + "; ".join(empty_pages[:20]))
        audit.extend(["Conceitos centrais identificados: " + "; ".join(retrieval_plan.concepts[:10])])
        audit.extend(["Possíveis erros dos alunos: " + "; ".join(retrieval_plan.possible_student_errors[:6])])
        self.last_analysis = analysis
        return GenerationResult(questions=questions, audit_messages=audit, theme_map=analysis.theme_map)

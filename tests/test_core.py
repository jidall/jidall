from __future__ import annotations

from pathlib import Path
import pytest
from document_readers.pdf_reader import PdfReader
from models.assessment import Alternative, GenerationRequest, GenerationResult, Operation, ProfileName, Question, ThemeMap
from profiles.rules import get_profile_rules
from services.generation_service import GenerationService
from services.errors import MissingPlanError
from validators.question_validator import QuestionValidator


class FakeProvider:
    def generate_questions(self, *, documents, theme_map, rules, quantity, operation, retrieved_context=None, only_selected_materials=True):
        qs = []
        labels = rules.objective_labels
        for idx in range(quantity):
            alternatives = [Alternative(label=l, text=f"Alternativa {l} com tamanho controlado", is_correct=(i == idx % len(labels)), justification="Justificativa baseada no material.") for i, l in enumerate(labels)]
            snippets = retrieved_context[idx] if retrieved_context and idx < len(retrieved_context) else []
            qs.append(Question(kind="objetiva", introduction="Texto introdutório " * 20, command="Assinale a alternativa correta.", alternatives=alternatives, reference="Referência: Aula 3.", difficulty="média", bloom_taxonomy="Compreender", source_snippets=snippets))
        return qs


def make_pdf(path: Path, lines: list[str]) -> None:
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    for line in lines:
        page = doc.new_page()
        page.insert_text((72, 72), line)
    doc.save(path)
    doc.close()


def test_pdf_reader_preserves_pages(tmp_path: Path):
    pdf = tmp_path / "texto_aula_3.pdf"
    make_pdf(pdf, ["Aula 3 Tema 1 Conteúdo", "Aula 3 Tema 2 Conteúdo"])
    doc = PdfReader().read(pdf)
    assert len(doc.pages) == 2
    assert doc.pages[1].page_number == 2
    assert "Tema 2" in doc.pages[1].text


def test_profile_identification():
    assert get_profile_rules(ProfileName.GRADE_ANTIGA).objective_alternatives == 5
    assert get_profile_rules(ProfileName.MARCO_REGULATORIO).objective_alternatives == 4


def test_validator_counts_characters_and_alternatives():
    q = Question(kind="objetiva", introduction="curta", command="Assinale a alternativa correta.", alternatives=[Alternative("A", "a", True, "j")], reference="Ref")
    messages = QuestionValidator().validate([q], get_profile_rules(ProfileName.GRADE_ANTIGA), 1)
    assert any("introdução" in msg for msg in messages)
    assert any("alternativas" in msg for msg in messages)


def test_answer_distribution_warning():
    rules = get_profile_rules(ProfileName.GRADE_ANTIGA)
    questions = []
    for _ in range(6):
        questions.append(Question(kind="objetiva", introduction="Intro " * 60, command="Assinale a alternativa correta.", alternatives=[Alternative(l, "Texto equilibrado", l == "A", "Just") for l in rules.objective_labels], reference="Ref"))
    assert any("gabaritos" in msg for msg in QuestionValidator().validate(questions, rules, 6))


def test_word_generation(tmp_path: Path):
    pytest.importorskip("docx")
    from exporters.word_exporter import WordExporter
    result = GenerationResult([Question(kind="discursiva", introduction="Intro " * 60, command="Responda entre 1000 e 3000 caracteres.", answer="Resposta esperada.", reference="Referência: Aula 3.")], [], ThemeMap("Aula 3", ["Tema"], []))
    questions, answers, audit = WordExporter().export(result, tmp_path, "saida")
    assert questions.name == "Questoes.docx"
    assert answers.name == "Gabarito.docx"
    assert audit.name == "Relatorio_Auditoria.docx"
    assert questions.exists()
    assert answers.exists()
    assert audit.exists()


def test_grade_antiga_without_plan_runs(tmp_path: Path):
    pdf = tmp_path / "texto_aula_3.pdf"
    make_pdf(pdf, ["Aula 3 Tema 1 Conteúdo"])
    req = GenerationRequest(ProfileName.GRADE_ANTIGA, Operation.APENAS_OBJETIVAS, "Aula 3", 2, tmp_path, "out", [pdf])
    result = GenerationService(FakeProvider()).generate(req)
    assert len(result.questions) == 2


def test_marco_regulatorio_blocks_without_plan(tmp_path: Path):
    pdf = tmp_path / "texto_aula_3.pdf"
    make_pdf(pdf, ["Aula 3 Tema 1 Conteúdo"])
    req = GenerationRequest(ProfileName.MARCO_REGULATORIO, Operation.APENAS_OBJETIVAS, "Aula 3", 1, tmp_path, "out", [pdf])
    with pytest.raises(MissingPlanError):
        GenerationService(FakeProvider()).generate(req)


def test_content_analyzer_summary_without_pdf_dependency():
    from framework.content_analyzer import ContentAnalyzer
    from models.assessment import SourceDocument, SourcePage
    doc = SourceDocument(Path("texto.pdf"), "texto da aula", [SourcePage("texto.pdf", "texto.pdf", 1, "Aula 3 Tema 1 Fundamentos do conteúdo")])
    analysis = ContentAnalyzer().analyze([doc], "Aula 3")
    assert "1 documento" in analysis.summary
    assert analysis.total_pages == 1
    assert analysis.theme_map.themes


def test_local_mvp_provider_generates_questions_without_api():
    from ai.test_provider import TestQuestionProvider
    from models.assessment import ThemeMap
    rules = get_profile_rules(ProfileName.GRADE_ANTIGA)
    questions = TestQuestionProvider().generate_questions(documents=[], theme_map=ThemeMap("Aula 3", ["Tema 1"], []), rules=rules, quantity=2, operation="gerar")
    assert len(questions) == 2
    assert len(questions[0].alternatives) == 5


def test_marco_regulatorio_with_plan_is_allowed_by_brain(tmp_path: Path):
    from framework.brain import Brain
    req = GenerationRequest(ProfileName.MARCO_REGULATORIO, Operation.BANCO_COMPLETO, "Aula 3", 65, tmp_path, "out", [])
    rules = Brain().decide_rules(req, {"texto da aula", "plano de ensino"})
    assert rules.requires_plan_competences
    assert rules.objective_alternatives == 4


def test_ai_question_provider_cancel_delegates_to_local_provider():
    from ai.question_provider import AIQuestionProvider

    class FakeAIProvider:
        cancelled = False
        def cancel_generation(self):
            self.cancelled = True
        def generate_structured(self, request):
            return {"questions": []}

    provider = FakeAIProvider()
    AIQuestionProvider(provider, "local-model").cancel_generation()
    assert provider.cancelled



def test_rag_retriever_preserves_source_traceability():
    from services.rag_retriever import RagRetriever
    from models.assessment import SourceDocument, SourcePage, ThemeMap
    doc = SourceDocument(Path("texto.pdf"), "texto da aula", [SourcePage("texto.pdf", "texto.pdf", 3, "Aula 3 Tema 2 Avaliação formativa e feedback", "texto da aula", "Aula 3", "Tema 2 Avaliação")])
    plan = RagRetriever().build_plan([doc], ThemeMap("Aula 3", ["Avaliação"], []), 1)
    snippet = plan.snippets_by_question[0][0]
    assert snippet.document_name == "texto.pdf"
    assert snippet.aula == "Aula 3"
    assert snippet.theme == "Tema 2 Avaliação"
    assert snippet.page_number == 3


def test_generation_request_defaults_to_only_selected_materials(tmp_path: Path):
    req = GenerationRequest(ProfileName.GRADE_ANTIGA, Operation.APENAS_OBJETIVAS, "Aula 1", 1, tmp_path, "out", [])
    assert req.only_selected_materials is True

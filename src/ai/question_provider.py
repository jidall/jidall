from __future__ import annotations

import json
import re
from typing import Protocol
from ai.providers import AIProvider, AIRequest
from models.assessment import Alternative, Question, SourceDocument, SourceSnippet, ThemeMap
from profiles.rules import ProfileRules


class QuestionProvider(Protocol):
    def generate_questions(self, *, documents: list[SourceDocument], theme_map: ThemeMap, rules: ProfileRules, quantity: int, operation: str, retrieved_context: list[list[SourceSnippet]] | None = None, only_selected_materials: bool = True) -> list[Question]: ...


class AIQuestionProvider:
    def __init__(self, ai_provider: AIProvider, model: str) -> None:
        self.ai_provider = ai_provider
        self.model = model

    def cancel_generation(self) -> None:
        self.ai_provider.cancel_generation()

    def generate_questions(self, *, documents: list[SourceDocument], theme_map: ThemeMap, rules: ProfileRules, quantity: int, operation: str, retrieved_context: list[list[SourceSnippet]] | None = None, only_selected_materials: bool = True) -> list[Question]:
        request = AIRequest(
            model=self.model,
            prompt=self._prompt(theme_map, rules, quantity, operation, self._chunks(documents), retrieved_context or [], only_selected_materials),
            system_prompt="Você gera questões avaliativas em JSON, usando exclusivamente os materiais fornecidos.",
            temperature=0.2,
        )
        payload = self._generate_json_with_retries(request)
        questions = [self._question(item) for item in payload.get("questions", []) if self._is_complete(item)]
        for index, question in enumerate(questions):
            if retrieved_context and index < len(retrieved_context):
                question.source_snippets = retrieved_context[index]
        return questions


    def _generate_json_with_retries(self, request: AIRequest, attempts: int = 3) -> dict:
        last_text = ""
        for attempt in range(attempts):
            text = self.ai_provider.generate(request)
            last_text = text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                repaired = self._repair_json(text)
                if repaired:
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        pass
                request = AIRequest(
                    prompt=request.prompt + "\n\nA resposta anterior não foi JSON válido. Reenvie somente JSON válido no schema solicitado, sem comentários.",
                    model=request.model,
                    system_prompt=request.system_prompt,
                    temperature=request.temperature,
                    timeout_seconds=request.timeout_seconds,
                )
        return {"questions": [], "error": "JSON inválido após tentativas", "raw_response": last_text[:2000]}

    def _repair_json(self, text: str) -> str | None:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S | re.I)
        if fenced:
            text = fenced.group(1)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start:end + 1]
        return None

    def _is_complete(self, item: dict) -> bool:
        if not item.get("introduction") or not item.get("command") or not item.get("reference"):
            return False
        if item.get("kind", "objetiva") == "objetiva" and not item.get("alternatives"):
            return False
        return True

    def _chunks(self, documents: list[SourceDocument], limit: int = 12000) -> list[str]:
        blocks: list[str] = []
        current = ""
        for doc in documents:
            for page in doc.pages:
                block = f"Arquivo: {page.file_name}\nTipo: {page.document_type}\nAula: {page.aula or 'não identificada'}\nTema: {page.theme or 'não identificado'}\nPágina: {page.page_number}\n{page.text}\n"
                if len(current) + len(block) > limit:
                    blocks.append(current)
                    current = block
                else:
                    current += "\n" + block
        if current:
            blocks.append(current)
        return blocks[:8]

    def _prompt(self, theme_map: ThemeMap, rules: ProfileRules, quantity: int, operation: str, chunks: list[str], retrieved_context: list[list[SourceSnippet]], only_selected_materials: bool) -> str:
        retrieved_payload = [[{
            "documento": snippet.document_name,
            "tipo": snippet.document_type,
            "aula": snippet.aula,
            "tema": snippet.theme,
            "pagina": snippet.page_number,
            "trecho": snippet.text,
            "score": snippet.score,
        } for snippet in snippets] for snippets in retrieved_context]
        return json.dumps({
            "instruction": "Responda somente JSON válido. Use exclusivamente os trechos recuperados e os materiais fornecidos quando only_selected_materials=true. Não use conhecimento externo, não invente conteúdo, competências ou habilidades. Gere questões completas e revisadas.",
            "only_selected_materials": only_selected_materials,
            "profile": rules.profile.value,
            "operation": operation,
            "quantity": quantity,
            "objective_alternatives": rules.objective_alternatives,
            "labels": rules.objective_labels,
            "min_introduction_chars": rules.min_introduction_chars,
            "requires_plan_competences": rules.requires_plan_competences,
            "themes": theme_map.themes,
            "profile_rules": {"category_distribution": rules.category_distribution, "difficulty_distribution": rules.difficulty_distribution, "reference_format": rules.reference_format, "grade_antiga": "10 objetivas e 5 discursivas por aula; objetivas A-E; respostas discursivas curtas; Bloom obrigatório.", "marco_regulatorio": "20 disciplinares, 15 formação geral, 15 interdisciplinares e 15 discursivas; objetivas A-D; competências e habilidades somente do Plano de Ensino; discursivas com comando exigindo 1000 a 3000 caracteres."},
            "quality_rules": ["introdução com no mínimo 250 caracteres", "comando positivo", "uma única alternativa correta", "justificativa individual de cada alternativa", "alternativas de tamanho e estrutura semelhantes", "referência com aula, tema e página quando disponível", "não usar comandos negativos", "não criar pistas óbvias"],
            "schemas": {"objective_question": {"numero": "int", "perfil": "str", "grupo": "str", "dificuldade": "str", "bloom": "str", "introducao": "str", "comando": "str", "alternativas": "list", "alternativa_correta": "str", "justificativas": "dict", "referencia": "str", "fontes_utilizadas": "list", "competencia": "str", "habilidade": "str"}, "discursive_question": {"numero": "int", "introducao": "str", "comando": "str", "padrao_resposta": "str", "referencia": "str", "fontes_utilizadas": "list", "competencia": "str", "habilidade": "str"}, "audit_report": {"falhas": "list", "limitacoes": "list"}, "content_summary": {"temas": "list", "conceitos": "list"}, "theme_map": {"aula": "str", "temas": "list"}},
            "required_schema": {"questions": [{"kind": "objetiva|discursiva", "category": "disciplinar|formação geral|interdisciplinar|", "introduction": "", "command": "", "alternatives": [{"label": "A", "text": "", "is_correct": True, "justification": ""}], "answer": "", "reference": "", "difficulty": "", "bloom_taxonomy": "", "competence": "", "skill": ""}]},
            "retrieved_context_by_question": retrieved_payload,
            "materials": chunks,
        }, ensure_ascii=False)

    def _question(self, item: dict) -> Question:
        return Question(
            kind=item.get("kind", "objetiva"),
            introduction=item.get("introduction", ""),
            category=item.get("category") or None,
            command=item.get("command", ""),
            alternatives=[Alternative(**alt) for alt in item.get("alternatives", [])],
            answer=item.get("answer", ""),
            reference=item.get("reference", ""),
            difficulty=item.get("difficulty") or None,
            bloom_taxonomy=item.get("bloom_taxonomy") or None,
            competence=item.get("competence") or None,
            skill=item.get("skill") or None,
        )

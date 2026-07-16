from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Protocol
from ai.providers import AIProvider, AIRequest
from models.assessment import Alternative, Question, SourceDocument, SourceSnippet, ThemeMap
from profiles.rules import ProfileRules

MAX_INPUT_CHARS = 24000
BATCH_SIZE = 3


class QuestionProvider(Protocol):
    def generate_questions(self, *, documents: list[SourceDocument], theme_map: ThemeMap, rules: ProfileRules, quantity: int, operation: str, retrieved_context: list[list[SourceSnippet]] | None = None, only_selected_materials: bool = True) -> list[Question]: ...


class AIQuestionProvider:
    def __init__(self, ai_provider: AIProvider, model: str) -> None:
        self.ai_provider = ai_provider
        self.model = model
        self.generation_notes: list[str] = []

    def cancel_generation(self) -> None:
        self.ai_provider.cancel_generation()

    def generate_questions(self, *, documents: list[SourceDocument], theme_map: ThemeMap, rules: ProfileRules, quantity: int, operation: str, retrieved_context: list[list[SourceSnippet]] | None = None, only_selected_materials: bool = True) -> list[Question]:
        self.generation_notes = []
        all_questions: list[Question] = []
        retrieved_context = retrieved_context or []
        for start in range(0, quantity, BATCH_SIZE):
            batch_context = retrieved_context[start:start + BATCH_SIZE]
            batch_quantity = min(BATCH_SIZE, quantity - start)
            prompt = self._prompt(theme_map, rules, batch_quantity, operation, batch_context, only_selected_materials, start + 1)
            request = AIRequest(
                model=self.model,
                prompt=prompt,
                system_prompt="Você gera questões avaliativas em JSON, usando exclusivamente os materiais fornecidos.",
                temperature=0.2,
                timeout_seconds=240,
                max_tokens=3500,
                response_format=self._response_schema(),
            )
            payload = self._generate_json_with_retries(request)
            batch_questions = [self._question(item) for item in self._items(payload) if self._is_complete(item)]
            for offset, question in enumerate(batch_questions):
                context_index = start + offset
                if retrieved_context and context_index < len(retrieved_context):
                    question.source_snippets = retrieved_context[context_index]
            all_questions.extend(batch_questions)
            self._save_partial_batch(start // BATCH_SIZE + 1, batch_questions)
        return all_questions[:quantity]

    def _generate_json_with_retries(self, request: AIRequest, attempts: int = 2) -> dict:
        last_text = ""
        try:
            text = self.ai_provider.generate(request)
            last_text = text
            parsed = self._parse_json(text)
            if parsed is not None:
                self.generation_notes.append("Geração com response_format json_schema.")
                return parsed
        except RuntimeError as exc:
            if "Status HTTP: 400" not in str(exc) and "HTTP 400" not in str(exc):
                raise
            self.generation_notes.append("LM Studio recusou json_schema; fallback sem response_format. Detalhe: " + str(exc)[:1000])
        fallback_request = AIRequest(
            prompt=request.prompt + "\n\nIMPORTANTE: responda somente JSON válido no schema solicitado, sem markdown e sem comentários.",
            model=request.model,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            timeout_seconds=request.timeout_seconds,
            max_tokens=request.max_tokens,
            response_format=None,
        )
        for attempt in range(attempts):
            text = self.ai_provider.generate(fallback_request)
            last_text = text
            parsed = self._parse_json(text)
            if parsed is not None:
                self.generation_notes.append("Geração em fallback sem response_format.")
                return parsed
            fallback_request = AIRequest(
                prompt=fallback_request.prompt + "\n\nA resposta anterior não foi JSON válido. Repare e reenvie somente JSON válido.",
                model=fallback_request.model,
                system_prompt=fallback_request.system_prompt,
                temperature=fallback_request.temperature,
                timeout_seconds=fallback_request.timeout_seconds,
                max_tokens=fallback_request.max_tokens,
            )
        self.generation_notes.append("JSON inválido após tentativas. Resposta inicial: " + last_text[:1000])
        return {"questions": [], "error": "JSON inválido após tentativas", "raw_response": last_text[:2000]}

    def _parse_json(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            repaired = self._repair_json(text)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    return None
        return None

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
        normalized = self._normalize_item(item)
        if not normalized.get("introduction") or not normalized.get("command") or not normalized.get("reference"):
            return False
        if normalized.get("kind", "objetiva") == "objetiva" and not normalized.get("alternatives"):
            return False
        return True

    def _prompt(self, theme_map: ThemeMap, rules: ProfileRules, quantity: int, operation: str, retrieved_context: list[list[SourceSnippet]], only_selected_materials: bool, first_number: int) -> str:
        retrieved_payload = [[{
            "documento": snippet.document_name,
            "tipo": snippet.document_type,
            "aula": snippet.aula,
            "tema": snippet.theme,
            "pagina": snippet.page_number,
            "trecho": snippet.text[:1200],
            "score": snippet.score,
        } for snippet in snippets] for snippets in retrieved_context]
        payload = {
            "instruction": "Responda somente JSON válido. Use exclusivamente os trechos recuperados quando only_selected_materials=true. Se os trechos forem insuficientes, não invente: retorne menos questões completas.",
            "only_selected_materials": only_selected_materials,
            "profile": rules.profile.value,
            "operation": operation,
            "first_question_number": first_number,
            "quantity": quantity,
            "objective_alternatives": rules.objective_alternatives,
            "labels": rules.objective_labels,
            "min_introduction_chars": rules.min_introduction_chars,
            "requires_plan_competences": rules.requires_plan_competences,
            "themes": theme_map.themes[:12],
            "profile_rules": {"category_distribution": rules.category_distribution, "difficulty_distribution": rules.difficulty_distribution, "reference_format": rules.reference_format},
            "quality_rules": ["introdução com no mínimo 250 caracteres", "comando positivo", "uma única alternativa correta", "justificativa individual de cada alternativa", "referência rastreável", "não usar comandos negativos"],
            "required_schema": {"questions": [{"kind": "objetiva|discursiva", "category": "", "introduction": "", "command": "", "alternatives": [{"label": "A", "text": "", "is_correct": True, "justification": ""}], "answer": "", "reference": "", "difficulty": "", "bloom_taxonomy": "", "competence": "", "skill": ""}]},
            "retrieved_context_by_question": retrieved_payload,
        }
        text = json.dumps(payload, ensure_ascii=False)
        return self._trim_prompt(text)

    def _trim_prompt(self, prompt: str) -> str:
        if len(prompt) <= MAX_INPUT_CHARS:
            return prompt
        self.generation_notes.append(f"Prompt reduzido de {len(prompt)} para {MAX_INPUT_CHARS} caracteres.")
        return prompt[:MAX_INPUT_CHARS] + "\n}"

    def _response_schema(self) -> dict:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "questoes_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "questoes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "numero": {"type": "integer"},
                                    "introducao": {"type": "string"},
                                    "comando": {"type": "string"},
                                    "alternativas": {"type": "array", "items": {"type": "string"}},
                                    "alternativa_correta": {"type": "string"},
                                    "justificativas": {"type": "array", "items": {"type": "string"}},
                                    "referencia": {"type": "string"},
                                },
                                "required": ["numero", "introducao", "comando", "alternativas", "alternativa_correta", "justificativas", "referencia"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["questoes"],
                    "additionalProperties": False,
                },
            },
        }

    def _items(self, payload: dict) -> list[dict]:
        return payload.get("questions") or payload.get("questoes") or []

    def _question(self, item: dict) -> Question:
        normalized = self._normalize_item(item)
        return Question(
            kind=normalized.get("kind", "objetiva"),
            introduction=normalized.get("introduction", ""),
            category=normalized.get("category") or None,
            command=normalized.get("command", ""),
            alternatives=[Alternative(**alt) for alt in normalized.get("alternatives", [])],
            answer=normalized.get("answer", ""),
            reference=normalized.get("reference", ""),
            difficulty=normalized.get("difficulty") or None,
            bloom_taxonomy=normalized.get("bloom_taxonomy") or None,
            competence=normalized.get("competence") or None,
            skill=normalized.get("skill") or None,
        )

    def _normalize_item(self, item: dict) -> dict:
        if "introducao" not in item:
            return item
        correct = item.get("alternativa_correta", "")
        justifications = item.get("justificativas", [])
        alternatives = []
        for index, text in enumerate(item.get("alternativas", [])):
            label = chr(ord("A") + index)
            alternatives.append({"label": label, "text": text, "is_correct": label == correct or text == correct, "justification": justifications[index] if index < len(justifications) else ""})
        return {
            "kind": "objetiva" if alternatives else "discursiva",
            "category": item.get("grupo"),
            "introduction": item.get("introducao", ""),
            "command": item.get("comando", ""),
            "alternatives": alternatives,
            "answer": item.get("padrao_resposta", ""),
            "reference": item.get("referencia", ""),
            "difficulty": item.get("dificuldade"),
            "bloom_taxonomy": item.get("bloom"),
            "competence": item.get("competencia"),
            "skill": item.get("habilidade"),
        }

    def _save_partial_batch(self, batch_number: int, questions: list[Question]) -> None:
        path = Path(tempfile.gettempdir()) / "assistente_provas_progress"
        path.mkdir(parents=True, exist_ok=True)
        data = [{"kind": q.kind, "reference": q.reference, "source_count": len(q.source_snippets)} for q in questions]
        (path / f"batch_{batch_number}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

from __future__ import annotations

import pytest
from ai.http_utils import HttpResponse
from ai.lmstudio_provider import LMStudioProvider
from ai.ollama_provider import OllamaProvider
from ai.openai_provider import OpenAIProvider
from ai.gemini_provider import GeminiProvider
from ai.claude_provider import ClaudeProvider
from ai.provider_factory import AIProviderConfig, create_provider, default_provider_config
from ai.providers import AIRequest, ProviderKind
from ai.question_provider import AIQuestionProvider
from models.assessment import SourceDocument, SourcePage, ThemeMap
from profiles.rules import get_profile_rules
from models.assessment import ProfileName


class FakeHttpClient:
    def __init__(self, responses=None, fail=False):
        self.responses = responses or {}
        self.fail = fail
        self.calls = []

    def get_json(self, url, timeout=10, headers=None):
        self.calls.append(("GET", url, headers))
        if self.fail:
            raise ConnectionRefusedError("refused")
        return HttpResponse(200, self.responses.get(url, {}))

    def post_json(self, url, payload, timeout=120, headers=None):
        self.calls.append(("POST", url, headers, payload))
        if self.fail:
            raise ConnectionRefusedError("refused")
        return HttpResponse(200, self.responses.get(url, {"response": '{"questions": []}'}))


def test_lmstudio_is_default_provider():
    config = default_provider_config()
    assert config.kind == ProviderKind.LM_STUDIO
    assert config.base_url == "http://127.0.0.1:1234/v1"
    assert isinstance(create_provider(config), LMStudioProvider)


def test_ollama_works_without_api_key_and_lists_models():
    client = FakeHttpClient({"http://localhost:11434/api/tags": {"models": [{"name": "llama3.1"}]}})
    provider = OllamaProvider(client=client)
    status = provider.test_connection()
    assert status.connected
    assert status.models == ["llama3.1"]
    assert "local" in status.message.lower()


def test_ollama_unavailable_is_detected():
    status = OllamaProvider(client=FakeHttpClient(fail=True)).test_connection()
    assert not status.connected
    assert status.status == "Serviço não iniciado"


def test_lmstudio_lists_models_and_factory_switches_provider():
    client = FakeHttpClient({"http://127.0.0.1:1234/v1/models": {"data": [{"id": "local-model"}]}})
    provider = LMStudioProvider(client=client)
    assert provider.list_models() == ["local-model"]
    assert provider.get_loaded_models() == ["local-model"]
    assert isinstance(create_provider(AIProviderConfig(kind=ProviderKind.LM_STUDIO, base_url="http://127.0.0.1:1234/v1", model="local-model")), LMStudioProvider)


def test_external_providers_require_explicit_api_key():
    for provider in (OpenAIProvider(api_key=None, client=FakeHttpClient()), GeminiProvider(api_key=None, client=FakeHttpClient()), ClaudeProvider(api_key=None, client=FakeHttpClient())):
        with pytest.raises(RuntimeError):
            provider.generate(__import__("ai.providers").providers.AIRequest(prompt="x", model="m"))


def test_local_mode_does_not_call_external_provider():
    client = FakeHttpClient({
        "http://localhost:11434/api/generate": {"response": '{"questions": []}'},
    })
    provider = OllamaProvider(client=client)
    AIQuestionProvider(provider, "llama3.1").generate_questions(
        documents=[SourceDocument(__import__("pathlib").Path("a.pdf"), "texto da aula", [SourcePage("a.pdf", "a.pdf", 1, "Aula 1 Tema 1")])],
        theme_map=ThemeMap("Aula 1", ["Tema 1"], []),
        rules=get_profile_rules(ProfileName.GRADE_ANTIGA),
        quantity=1,
        operation="gerar",
    )
    assert all("api.openai.com" not in call[1] for call in client.calls)
    assert any("localhost:11434" in call[1] for call in client.calls)


def test_ollama_generate_structured():
    client = FakeHttpClient({"http://localhost:11434/api/generate": {"response": '{"ok": true}'}})
    assert OllamaProvider(client=client).generate_structured(AIRequest(prompt="x", model="llama3.1")) == {"ok": True}


def test_ollama_reports_no_model_installed():
    client = FakeHttpClient({"http://localhost:11434/api/tags": {"models": []}})
    status = OllamaProvider(client=client).test_connection()
    assert status.connected
    assert status.status == "Modelo não instalado"
    assert "ollama pull" in status.message



def test_factory_supports_all_requested_providers():
    assert isinstance(create_provider(AIProviderConfig(kind=ProviderKind.OPENAI, base_url="https://api.openai.com/v1", model="gpt", api_key="k")), OpenAIProvider)
    assert isinstance(create_provider(AIProviderConfig(kind=ProviderKind.GEMINI, base_url="https://generativelanguage.googleapis.com/v1beta", model="gemini", api_key="k")), GeminiProvider)
    assert isinstance(create_provider(AIProviderConfig(kind=ProviderKind.CLAUDE, base_url="https://api.anthropic.com/v1", model="claude", api_key="k")), ClaudeProvider)


def test_gemini_and_claude_parse_generation_responses():
    gemini_client = FakeHttpClient({"https://generativelanguage.googleapis.com/v1beta/models/gemini:generateContent?key=k": {"candidates": [{"content": {"parts": [{"text": '{"questions": []}'}]}}]}})
    assert GeminiProvider(api_key="k", client=gemini_client).generate(__import__("ai.providers").providers.AIRequest(prompt="x", model="gemini")) == '{"questions": []}'
    claude_client = FakeHttpClient({"https://api.anthropic.com/v1/messages": {"content": [{"type": "text", "text": '{"questions": []}'}]}})
    assert ClaudeProvider(api_key="k", client=claude_client).generate(__import__("ai.providers").providers.AIRequest(prompt="x", model="claude")) == '{"questions": []}'



def test_lmstudio_connection_requires_model_response():
    client = FakeHttpClient({
        "http://127.0.0.1:1234/v1/models": {"data": [{"id": "google/gemma-4-e4b"}]},
        "http://127.0.0.1:1234/v1/chat/completions": {"choices": [{"message": {"content": "conexão válida"}}]},
    })
    status = LMStudioProvider(client=client).test_connection()
    assert status.connected
    assert status.message == "Conexão com LM Studio realizada com sucesso."


def test_lmstudio_no_models_is_not_success():
    client = FakeHttpClient({"http://127.0.0.1:1234/v1/models": {"data": []}})
    status = LMStudioProvider(client=client).test_connection()
    assert status.connected
    assert status.status == "Modelo indisponível"


def test_lmstudio_invalid_model_response_fails_connection():
    client = FakeHttpClient({
        "http://127.0.0.1:1234/v1/models": {"data": [{"id": "model"}]},
        "http://127.0.0.1:1234/v1/chat/completions": {"choices": [{"message": {"content": "sem json"}}]},
    })
    status = LMStudioProvider(client=client).test_connection()
    assert not status.connected
    assert status.message == "O modelo local não respondeu."


def test_ai_question_provider_repairs_fenced_json():
    class FakeAIProvider:
        def cancel_generation(self): pass
        def generate(self, request):
            return '```json\n{"questions": [{"kind": "discursiva", "introduction": "Intro", "command": "Comando", "reference": "Referência: Aula 1.", "answer": "Resposta"}]}\n```'
    provider = AIQuestionProvider(FakeAIProvider(), "model")
    questions = provider.generate_questions(documents=[], theme_map=ThemeMap("Aula 1", ["Tema"], []), rules=get_profile_rules(ProfileName.GRADE_ANTIGA), quantity=1, operation="gerar")
    assert len(questions) == 1


def test_ai_question_provider_rejects_invalid_json_after_retries():
    class FakeAIProvider:
        def cancel_generation(self): pass
        def generate(self, request): return "não json"
    provider = AIQuestionProvider(FakeAIProvider(), "model")
    assert provider.generate_questions(documents=[], theme_map=ThemeMap("Aula 1", ["Tema"], []), rules=get_profile_rules(ProfileName.GRADE_ANTIGA), quantity=1, operation="gerar") == []


def test_lmstudio_timeout_reports_failure():
    class TimeoutClient(FakeHttpClient):
        def post_json(self, url, payload, timeout=120, headers=None):
            raise TimeoutError("timeout")
    client = TimeoutClient({"http://127.0.0.1:1234/v1/models": {"data": [{"id": "model"}]}})
    status = LMStudioProvider(client=client).test_connection()
    assert not status.connected
    assert status.status in {"Erro", "Servidor desligado"}

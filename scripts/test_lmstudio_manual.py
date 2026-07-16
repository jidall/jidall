from __future__ import annotations

import json
from ai.http_utils import JsonHttpClient, HttpRequestError
from ai.providers import AIRequest
from ai.lmstudio_provider import LMStudioProvider
from ai.question_provider import AIQuestionProvider
from models.assessment import ThemeMap, ProfileName
from profiles.rules import get_profile_rules

BASE_URL = "http://127.0.0.1:1234/v1"
EXPECTED_MODEL = "google/gemma-4-e4b"
client = JsonHttpClient()


def show(label: str, fn):
    print("\n=== " + label + " ===")
    try:
        print(fn())
    except HttpRequestError as exc:
        print(exc.detailed_message())
    except Exception as exc:
        print(str(exc))


models_response = show("1. GET /v1/models", lambda: client.get_json(f"{BASE_URL}/models").data)
provider = LMStudioProvider(BASE_URL)
status = provider.test_connection()
print("\nStatus:", status.status, status.message)
print("Modelos:", status.models)
model = EXPECTED_MODEL if EXPECTED_MODEL in status.models else (status.models[0] if status.models else EXPECTED_MODEL)

show("2. Chamada mínima sem response_format", lambda: provider.generate(AIRequest(prompt="Responda apenas: conexão válida", model=model, max_tokens=50)))
show("3. Chamada com JSON simples", lambda: provider.generate(AIRequest(prompt='Responda somente JSON: {"teste":"ok"}', model=model, max_tokens=100)))
question_provider = AIQuestionProvider(provider, model)
show("4. Chamada com json_schema", lambda: json.dumps(question_provider._generate_json_with_retries(AIRequest(prompt='Gere uma questão simples no schema.', model=model, max_tokens=500, response_format=question_provider._response_schema())), ensure_ascii=False))

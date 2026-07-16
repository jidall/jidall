from __future__ import annotations

from ai.lmstudio_provider import LMStudioProvider
from ai.providers import AIRequest

BASE_URL = "http://127.0.0.1:1234/v1"
EXPECTED_MODEL = "google/gemma-4-e4b"

provider = LMStudioProvider(BASE_URL)
status = provider.test_connection()
print(status.status + ": " + status.message)
print("Modelos:", status.models)
model = EXPECTED_MODEL if EXPECTED_MODEL in status.models else (status.models[0] if status.models else EXPECTED_MODEL)
if status.connected:
    print(provider.generate(AIRequest(prompt='Responda em JSON: {"teste":"ok"}', model=model, timeout_seconds=120)))

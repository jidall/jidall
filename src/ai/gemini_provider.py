from __future__ import annotations

import json
from typing import Any
from ai.http_utils import JsonHttpClient, connection_error_message
from ai.providers import AIProvider, AIRequest, ProviderCapabilities, ProviderKind, ProviderParameter, ProviderStatus


class GeminiProvider(AIProvider):
    kind = ProviderKind.GEMINI

    @classmethod
    def capabilities(cls) -> ProviderCapabilities:
        return ProviderCapabilities(local=False, paid_or_external=True, parameters=[
            ProviderParameter("base_url", "Endereço da API", True, False, "https://generativelanguage.googleapis.com/v1beta"),
            ProviderParameter("api_key", "Chave da API", True, True, ""),
        ])

    def __init__(self, base_url: str = "https://generativelanguage.googleapis.com/v1beta", api_key: str | None = None, client: JsonHttpClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = client or JsonHttpClient()
        self._cancelled = False

    def _key_url(self, path: str) -> str:
        if not self.api_key:
            raise RuntimeError("Gemini exige chave de API configurada explicitamente.")
        return f"{self.base_url}{path}?key={self.api_key}"

    def list_models(self) -> list[str]:
        response = self.client.get_json(self._key_url("/models"), timeout=20)
        return [item.get("name", "").replace("models/", "") for item in response.data.get("models", []) if item.get("name")]

    def test_connection(self) -> ProviderStatus:
        try:
            models = self.list_models()
            return ProviderStatus(True, "Conectado", "Gemini conectado. Atenção: provedor externo pode gerar custos e enviar documentos para fora do computador.", models)
        except Exception as exc:
            return ProviderStatus(False, "Desconectado", connection_error_message(exc), [])

    def generate(self, request: AIRequest) -> str:
        self._cancelled = False
        text = f"{request.system_prompt or ''}\n\n{request.prompt}".strip()
        payload = {"contents": [{"parts": [{"text": text}]}], "generationConfig": {"temperature": request.temperature}}
        response = self.client.post_json(self._key_url(f"/models/{request.model}:generateContent"), payload, timeout=request.timeout_seconds)
        if self._cancelled:
            raise RuntimeError("Geração cancelada.")
        return response.data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    def generate_structured(self, request: AIRequest) -> dict[str, Any]:
        return json.loads(self.generate(request))

    def get_provider_status(self) -> ProviderStatus:
        return self.test_connection()

    def cancel_generation(self) -> None:
        self._cancelled = True

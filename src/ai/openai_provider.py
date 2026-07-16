from __future__ import annotations

import json
from typing import Any
from ai.http_utils import JsonHttpClient, connection_error_message
from ai.providers import AIProvider, AIRequest, ProviderCapabilities, ProviderKind, ProviderParameter, ProviderStatus


class OpenAIProvider(AIProvider):
    kind = ProviderKind.OPENAI

    @classmethod
    def capabilities(cls) -> ProviderCapabilities:
        return ProviderCapabilities(local=False, paid_or_external=True, parameters=[
            ProviderParameter("base_url", "Endereço da API", True, False, "https://api.openai.com/v1"),
            ProviderParameter("api_key", "Chave da API", True, True, ""),
        ])

    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: str | None = None, client: JsonHttpClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = client or JsonHttpClient()
        self._cancelled = False

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("OpenAI exige chave de API configurada explicitamente.")
        return {"Authorization": f"Bearer {self.api_key}"}

    def list_models(self) -> list[str]:
        response = self.client.get_json(f"{self.base_url}/models", timeout=20, headers=self._headers())
        return [item.get("id", "") for item in response.data.get("data", []) if item.get("id")]

    def test_connection(self) -> ProviderStatus:
        try:
            models = self.list_models()
            return ProviderStatus(True, "Conectado", "OpenAI conectado. Atenção: provedor externo pode gerar custos e enviar documentos para fora do computador.", models)
        except Exception as exc:
            return ProviderStatus(False, "Desconectado", connection_error_message(exc), [])

    def generate(self, request: AIRequest) -> str:
        self._cancelled = False
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload = {"model": request.model, "messages": messages, "temperature": request.temperature}
        response = self.client.post_json(f"{self.base_url}/chat/completions", payload, timeout=request.timeout_seconds, headers=self._headers())
        if self._cancelled:
            raise RuntimeError("Geração cancelada.")
        return response.data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def generate_structured(self, request: AIRequest) -> dict[str, Any]:
        return json.loads(self.generate(request))

    def get_provider_status(self) -> ProviderStatus:
        return self.test_connection()

    def cancel_generation(self) -> None:
        self._cancelled = True

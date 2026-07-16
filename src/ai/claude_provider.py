from __future__ import annotations

import json
from typing import Any
from ai.http_utils import JsonHttpClient, connection_error_message
from ai.providers import AIProvider, AIRequest, ProviderCapabilities, ProviderKind, ProviderParameter, ProviderStatus


class ClaudeProvider(AIProvider):
    kind = ProviderKind.CLAUDE

    @classmethod
    def capabilities(cls) -> ProviderCapabilities:
        return ProviderCapabilities(local=False, paid_or_external=True, parameters=[
            ProviderParameter("base_url", "Endereço da API", True, False, "https://api.anthropic.com/v1"),
            ProviderParameter("api_key", "Chave da API", True, True, ""),
            ProviderParameter("anthropic_version", "Anthropic-Version", True, False, "2023-06-01"),
        ])

    def __init__(self, base_url: str = "https://api.anthropic.com/v1", api_key: str | None = None, anthropic_version: str = "2023-06-01", client: JsonHttpClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.anthropic_version = anthropic_version
        self.client = client or JsonHttpClient()
        self._cancelled = False

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("Claude exige chave de API configurada explicitamente.")
        return {"x-api-key": self.api_key, "anthropic-version": self.anthropic_version}

    def list_models(self) -> list[str]:
        headers = self._headers()
        try:
            response = self.client.get_json(f"{self.base_url}/models", timeout=20, headers=headers)
            return [item.get("id", "") for item in response.data.get("data", []) if item.get("id")]
        except Exception:
            return ["claude-3-5-sonnet-latest"]

    def test_connection(self) -> ProviderStatus:
        try:
            models = self.list_models()
            return ProviderStatus(True, "Conectado", "Claude configurado. Atenção: provedor externo pode gerar custos e enviar documentos para fora do computador.", models)
        except Exception as exc:
            return ProviderStatus(False, "Desconectado", connection_error_message(exc), [])

    def generate(self, request: AIRequest) -> str:
        self._cancelled = False
        payload = {"model": request.model, "max_tokens": 4096, "temperature": request.temperature, "system": request.system_prompt or "", "messages": [{"role": "user", "content": request.prompt}]}
        response = self.client.post_json(f"{self.base_url}/messages", payload, timeout=request.timeout_seconds, headers=self._headers())
        if self._cancelled:
            raise RuntimeError("Geração cancelada.")
        content = response.data.get("content", [])
        return "".join(part.get("text", "") for part in content if part.get("type") == "text")

    def generate_structured(self, request: AIRequest) -> dict[str, Any]:
        return json.loads(self.generate(request))

    def get_provider_status(self) -> ProviderStatus:
        return self.test_connection()

    def cancel_generation(self) -> None:
        self._cancelled = True

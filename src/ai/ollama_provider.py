from __future__ import annotations

import json
from typing import Any
from ai.http_utils import JsonHttpClient, connection_error_message
from ai.providers import AIProvider, AIRequest, ProviderCapabilities, ProviderKind, ProviderParameter, ProviderStatus


class OllamaProvider(AIProvider):
    kind = ProviderKind.OLLAMA


    @classmethod
    def capabilities(cls) -> ProviderCapabilities:
        return ProviderCapabilities(local=True, paid_or_external=False, parameters=[ProviderParameter("base_url", "Endereço do servidor", True, False, "http://localhost:11434")])

    def __init__(self, base_url: str = "http://localhost:11434", client: JsonHttpClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or JsonHttpClient()
        self._cancelled = False

    def list_models(self) -> list[str]:
        response = self.client.get_json(f"{self.base_url}/api/tags", timeout=10)
        return [item.get("name", "") for item in response.data.get("models", []) if item.get("name")]

    def test_connection(self) -> ProviderStatus:
        try:
            models = self.list_models()
            if not models:
                return ProviderStatus(True, "Modelo não instalado", "Ollama conectado, mas nenhum modelo foi encontrado. Instale um modelo com: ollama pull llama3.1", [])
            return ProviderStatus(True, "Conectado", "Ollama local conectado. Processamento local ativo; documentos não serão enviados a serviços externos.", models)
        except Exception as exc:
            return ProviderStatus(False, "Serviço não iniciado", connection_error_message(exc), [])

    def generate(self, request: AIRequest) -> str:
        self._cancelled = False
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "system": request.system_prompt or "",
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        response = self.client.post_json(f"{self.base_url}/api/generate", payload, timeout=request.timeout_seconds)
        if self._cancelled:
            raise RuntimeError("Geração cancelada.")
        return response.data.get("response", "")

    def generate_structured(self, request: AIRequest) -> dict[str, Any]:
        text = self.generate(request)
        return json.loads(text)

    def get_provider_status(self) -> ProviderStatus:
        return self.test_connection()

    def cancel_generation(self) -> None:
        self._cancelled = True

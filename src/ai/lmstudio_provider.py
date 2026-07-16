from __future__ import annotations

import json
from typing import Any
from ai.http_utils import JsonHttpClient, connection_error_message
from ai.providers import AIProvider, AIRequest, ProviderCapabilities, ProviderKind, ProviderParameter, ProviderStatus


class LMStudioProvider(AIProvider):
    kind = ProviderKind.LM_STUDIO

    @classmethod
    def capabilities(cls) -> ProviderCapabilities:
        return ProviderCapabilities(local=True, paid_or_external=False, parameters=[ProviderParameter("base_url", "Endereço do servidor", True, False, "http://127.0.0.1:1234/v1")])

    def __init__(self, base_url: str = "http://127.0.0.1:1234/v1", client: JsonHttpClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or JsonHttpClient()
        self._cancelled = False

    def list_models(self) -> list[str]:
        response = self.client.get_json(f"{self.base_url}/models", timeout=10)
        return [item.get("id", "") for item in response.data.get("data", []) if item.get("id")]

    def get_loaded_models(self) -> list[str]:
        return self.list_models()

    def test_connection(self) -> ProviderStatus:
        try:
            models = self.list_models()
            if not models:
                return ProviderStatus(True, "Modelo indisponível", "Nenhum modelo está disponível no LM Studio.", [])
            probe = AIRequest(prompt='Responda exatamente: {"ok": true}', model=models[0], system_prompt="Responda somente JSON válido.", timeout_seconds=45)
            text = self.generate(probe).strip()
            if "ok" not in text.lower():
                return ProviderStatus(False, "Erro", "O modelo local não respondeu.", models)
            return ProviderStatus(True, "Conectado", "Conexão com LM Studio realizada com sucesso.", models)
        except RuntimeError as exc:
            return ProviderStatus(False, "Erro", str(exc), [])
        except Exception as exc:
            message = connection_error_message(exc)
            if "401" in message or "403" in message:
                return ProviderStatus(False, "Erro", "A autenticação do LM Studio está ativada e requer token.", [])
            return ProviderStatus(False, "Servidor desligado", "O servidor do LM Studio não está ativo.", [])

    def generate(self, request: AIRequest) -> str:
        self._cancelled = False
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload = {"model": request.model, "messages": messages, "temperature": request.temperature, "stream": False}
        last_error: Exception | None = None
        for _ in range(3):
            try:
                response = self.client.post_json(f"{self.base_url}/chat/completions", payload, timeout=request.timeout_seconds)
                if self._cancelled:
                    raise RuntimeError("Geração cancelada.")
                return response.data.get("choices", [{}])[0].get("message", {}).get("content", "")
            except TimeoutError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc
        raise RuntimeError(connection_error_message(last_error or RuntimeError("Falha desconhecida no LM Studio.")))

    def generate_structured(self, request: AIRequest) -> dict[str, Any]:
        return json.loads(self.generate(request))

    def get_provider_status(self) -> ProviderStatus:
        return self.test_connection()

    def get_status(self) -> ProviderStatus:
        return self.get_provider_status()

    def cancel_generation(self) -> None:
        self._cancelled = True

    def cancel(self) -> None:
        self.cancel_generation()

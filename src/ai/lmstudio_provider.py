from __future__ import annotations

import json
from typing import Any
from ai.http_utils import HttpRequestError, JsonHttpClient, connection_error_message
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
        self.last_error_detail = ""
        self.last_payload_summary: dict[str, Any] = {}

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
            probe = AIRequest(prompt="Responda apenas: conexão válida", model=models[0], timeout_seconds=45, max_tokens=50)
            text = self.generate(probe).strip().lower()
            if "conexão válida" not in text and "conexao valida" not in text:
                return ProviderStatus(False, "Erro", "O modelo local não respondeu.", models)
            return ProviderStatus(True, "Conectado", "Conexão com LM Studio realizada com sucesso.", models)
        except RuntimeError as exc:
            return ProviderStatus(False, "Erro", str(exc), [])
        except Exception as exc:
            message = connection_error_message(exc)
            if "401" in message or "403" in message:
                return ProviderStatus(False, "Erro", "A autenticação do LM Studio está ativada e requer token.", [])
            return ProviderStatus(False, "Servidor desligado", "O servidor do LM Studio não está ativo. Abra o LM Studio, acesse Developer > Local Server e ative Status: Running.", [])

    def generate(self, request: AIRequest) -> str:
        self._cancelled = False
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 2048,
            "stream": False,
        }
        if request.response_format:
            payload["response_format"] = request.response_format
        self.last_payload_summary = self._payload_summary(payload, request.prompt)
        last_error: Exception | None = None
        for _ in range(3):
            try:
                response = self.client.post_json(f"{self.base_url}/chat/completions", payload, timeout=request.timeout_seconds)
                if self._cancelled:
                    raise RuntimeError("Geração cancelada.")
                return response.data.get("choices", [{}])[0].get("message", {}).get("content", "")
            except HttpRequestError as exc:
                self.last_error_detail = self._format_http_error(exc, payload, request.prompt)
                raise RuntimeError(self.last_error_detail) from exc
            except TimeoutError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc
        detail = connection_error_message(last_error or RuntimeError("Falha desconhecida no LM Studio."))
        self.last_error_detail = detail
        raise RuntimeError(detail)

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

    def _payload_summary(self, payload: dict[str, Any], prompt: str) -> dict[str, Any]:
        return {
            "model": payload.get("model"),
            "message_count": len(payload.get("messages", [])),
            "prompt_chars": len(prompt),
            "parameters": {key: value for key, value in payload.items() if key != "messages"},
        }

    def _format_http_error(self, exc: HttpRequestError, payload: dict[str, Any], prompt: str) -> str:
        summary = self._payload_summary(payload, prompt)
        return (
            f"Falha ao chamar LM Studio.\n"
            f"URL chamada: {exc.url}\n"
            f"Modelo: {summary['model']}\n"
            f"Status HTTP: {exc.status}\n"
            f"Mensagem HTTP: {exc.reason}\n"
            f"Corpo da resposta: {exc.body}\n"
            f"Tamanho aproximado do prompt: {summary['prompt_chars']} caracteres\n"
            f"Número de mensagens: {summary['message_count']}\n"
            f"Parâmetros enviados: {summary['parameters']}"
        )

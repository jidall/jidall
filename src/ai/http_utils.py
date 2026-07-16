from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HttpResponse:
    status: int
    data: Any


class HttpRequestError(RuntimeError):
    def __init__(self, url: str, status: int | None, reason: str, body: str = "") -> None:
        super().__init__(f"HTTP {status}: {reason}" if status else reason)
        self.url = url
        self.status = status
        self.reason = reason
        self.body = body

    def detailed_message(self) -> str:
        return f"URL: {self.url}\nStatus HTTP: {self.status}\nMotivo: {self.reason}\nCorpo: {self.body}"


class JsonHttpClient:
    def get_json(self, url: str, timeout: int = 10, headers: dict[str, str] | None = None) -> HttpResponse:
        request = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-configured local/compatible endpoint
                return HttpResponse(response.status, json.loads(response.read().decode("utf-8") or "{}"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise HttpRequestError(url, exc.code, exc.reason, body) from exc

    def post_json(self, url: str, payload: dict[str, Any], timeout: int = 120, headers: dict[str, str] | None = None) -> HttpResponse:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-configured local/compatible endpoint
                return HttpResponse(response.status, json.loads(response.read().decode("utf-8") or "{}"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise HttpRequestError(url, exc.code, exc.reason, body) from exc


def connection_error_message(exc: Exception) -> str:
    if isinstance(exc, HttpRequestError):
        return exc.detailed_message()
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}: {exc.reason}"
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, ConnectionRefusedError):
            return "Serviço não iniciado ou porta recusada."
        if isinstance(reason, socket.timeout):
            return "Tempo limite esgotado."
        return str(reason)
    if isinstance(exc, TimeoutError):
        return "Tempo limite esgotado."
    return str(exc)

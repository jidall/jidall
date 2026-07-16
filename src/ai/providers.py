from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderKind(str, Enum):
    LM_STUDIO = "LM Studio Local — gratuito"
    OLLAMA = "Ollama Local — gratuito"
    OPENAI = "OpenAI — externo"
    GEMINI = "Gemini — externo"
    CLAUDE = "Claude — externo"


@dataclass(frozen=True)
class ProviderStatus:
    connected: bool
    status: str
    message: str
    models: list[str]


@dataclass(frozen=True)
class AIRequest:
    prompt: str
    model: str
    system_prompt: str | None = None
    temperature: float = 0.2
    timeout_seconds: int = 120


@dataclass(frozen=True)
class ProviderParameter:
    name: str
    label: str
    required: bool = False
    secret: bool = False
    default: str = ""


@dataclass(frozen=True)
class ProviderCapabilities:
    local: bool
    paid_or_external: bool
    parameters: list[ProviderParameter] = field(default_factory=list)


class AIProvider(ABC):
    kind: ProviderKind

    @abstractmethod
    def list_models(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> ProviderStatus:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: AIRequest) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(self, request: AIRequest) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_provider_status(self) -> ProviderStatus:
        raise NotImplementedError

    @abstractmethod
    def cancel_generation(self) -> None:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def capabilities(cls) -> ProviderCapabilities:
        raise NotImplementedError

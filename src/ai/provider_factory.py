from __future__ import annotations

from dataclasses import dataclass
from ai.claude_provider import ClaudeProvider
from ai.gemini_provider import GeminiProvider
from ai.lmstudio_provider import LMStudioProvider
from ai.ollama_provider import OllamaProvider
from ai.openai_provider import OpenAIProvider
from ai.providers import AIProvider, ProviderKind


@dataclass(frozen=True)
class AIProviderConfig:
    kind: ProviderKind = ProviderKind.LM_STUDIO
    base_url: str = "http://127.0.0.1:1234/v1"
    model: str = "local-model"
    api_key: str | None = None
    anthropic_version: str = "2023-06-01"


def default_provider_config() -> AIProviderConfig:
    return AIProviderConfig()


def create_provider(config: AIProviderConfig) -> AIProvider:
    if config.kind == ProviderKind.LM_STUDIO:
        return LMStudioProvider(config.base_url)
    if config.kind == ProviderKind.OLLAMA:
        return OllamaProvider(config.base_url)
    if config.kind == ProviderKind.OPENAI:
        return OpenAIProvider(config.base_url, config.api_key)
    if config.kind == ProviderKind.GEMINI:
        return GeminiProvider(config.base_url, config.api_key)
    return ClaudeProvider(config.base_url, config.api_key, config.anthropic_version)

from __future__ import annotations

import os
import keyring
from ai.provider_factory import AIProviderConfig
from ai.providers import ProviderKind

SERVICE = "Assistente de Provas"
USER = "external_api_key"


class Settings:
    def get_api_key(self) -> str | None:
        return os.getenv("AI_PROVIDER_API_KEY") or os.getenv("OPENAI_API_KEY") or keyring.get_password(SERVICE, USER)

    def set_api_key(self, api_key: str) -> None:
        keyring.set_password(SERVICE, USER, api_key)

    def default_ai_config(self) -> AIProviderConfig:
        return AIProviderConfig(kind=ProviderKind.LM_STUDIO, base_url="http://127.0.0.1:1234/v1", model="local-model", api_key=None)

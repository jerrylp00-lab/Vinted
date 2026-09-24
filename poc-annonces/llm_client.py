"""Client OpenRouter partagé (SDK OpenAI, base_url OpenRouter)."""

from __future__ import annotations

import os

from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
FALLBACK_MODELS = ["openai/gpt-4o-mini", "anthropic/claude-haiku-4.5"]


class OpenRouterKeyMissing(Exception):
    """Clé OPENROUTER_API_KEY manquante dans l'environnement."""


def build_openrouter_client(client: OpenAI | None = None) -> OpenAI:
    if client is not None:
        return client

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterKeyMissing(
            "OPENROUTER_API_KEY manquante dans l'environnement. "
            "Voir .env.example pour la configuration."
        )
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


def resolve_model(model: str | None = None) -> str:
    return model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL

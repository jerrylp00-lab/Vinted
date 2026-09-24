# image_gen.py
"""PoC-2 V2 : génération d'image par modèle image natif, via OpenRouter.

Frontière testable : generate_image(prompt, references) -> GeneratedImage.
Les tests mockent la session HTTP (requests), jamais le décodage de l'image.
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass

import requests
from PIL import Image

from images import resize_to_data_url

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_IMAGE_MODEL = "google/gemini-3.1-flash-image"
REQUEST_TIMEOUT_SECONDS = 300


class ImageGenerationError(Exception):
    """Erreur lors de la génération d'une image."""


@dataclass
class GeneratedImage:
    image: Image.Image
    cost: float


def generate_image(
    prompt: str,
    references: list[bytes],
    model: str | None = None,
    session: requests.Session | None = None,
    api_key: str | None = None,
) -> GeneratedImage:
    """Envoie `prompt` + `references` (images brutes) au modèle image, renvoie 1 image."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ImageGenerationError(
            "OPENROUTER_API_KEY manquante dans l'environnement. Voir .env.example."
        )
    resolved_model = model or os.environ.get("OPENROUTER_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL
    http = session or requests.Session()

    content = [{"type": "text", "text": prompt}] + [
        {"type": "image_url", "image_url": {"url": resize_to_data_url(ref)}}
        for ref in references
    ]
    body = {
        "model": resolved_model,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": content}],
        "usage": {"include": True},
    }

    try:
        response = http.post(
            OPENROUTER_CHAT_URL,
            headers={"Authorization": f"Bearer {key}"},
            json=body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ImageGenerationError(f"Appel au modèle image échoué : {exc}") from exc

    if response.status_code != 200:
        raise ImageGenerationError(
            f"Modèle image : HTTP {response.status_code} — {response.text[:200]}"
        )

    payload = response.json()
    try:
        data_url = payload["choices"][0]["message"]["images"][0]["image_url"]["url"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ImageGenerationError("Le modèle n'a renvoyé aucune image.") from exc

    try:
        raw = base64.b64decode(data_url.split(",", 1)[1])
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise ImageGenerationError(f"Image renvoyée illisible : {exc}") from exc

    cost = float((payload.get("usage") or {}).get("cost") or 0.0)
    return GeneratedImage(image=image, cost=cost)

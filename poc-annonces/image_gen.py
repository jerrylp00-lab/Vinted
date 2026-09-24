"""PoC-2 V2 : génération d'image par modèle image natif (Nano Banana 2 / Gemini image), via Fal.ai.

Frontière testable : generate_image(prompt, references) -> GeneratedImage.
Les tests mockent la session HTTP (requests), jamais le décodage de l'image.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass

import requests
from PIL import Image

from images import resize_to_data_url

FAL_BASE_URL = "https://fal.run"
DEFAULT_IMAGE_MODEL = "fal-ai/nano-banana-2/edit"
ASPECT_RATIO = "3:4"  # portrait, adapté aux photos Vinted
RESOLUTION = "1K"
# Fal ne renvoie pas le prix dans la réponse : estimation d'après la grille
# publique (1K = 0,08 $/image), multipliée par `x-fal-billable-units`.
COST_PER_UNIT_USD = 0.08
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
    key = api_key or os.environ.get("FAL_KEY")
    if not key:
        raise ImageGenerationError("FAL_KEY manquante dans l'environnement. Voir AGENTS.md.")
    resolved_model = model or os.environ.get("FAL_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL
    http = session or requests.Session()

    body = {
        "prompt": prompt,
        "image_urls": [resize_to_data_url(ref) for ref in references],
        "aspect_ratio": ASPECT_RATIO,
        "resolution": RESOLUTION,
        "output_format": "png",
        "num_images": 1,
    }

    try:
        response = http.post(
            f"{FAL_BASE_URL}/{resolved_model}",
            headers={"Authorization": f"Key {key}"},
            json=body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ImageGenerationError(f"Appel au modèle image échoué : {exc}") from exc

    if response.status_code != 200:
        raise ImageGenerationError(
            f"Modèle image : HTTP {response.status_code} — {response.text[:200]}"
        )

    try:
        image_url = response.json()["images"][0]["url"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ImageGenerationError("Le modèle n'a renvoyé aucune image.") from exc

    try:
        download = http.get(image_url, timeout=REQUEST_TIMEOUT_SECONDS)
        download.raise_for_status()
        image = Image.open(io.BytesIO(download.content)).convert("RGB")
    except Exception as exc:
        raise ImageGenerationError(f"Image renvoyée illisible : {exc}") from exc

    units = float(response.headers.get("x-fal-billable-units") or 1.0)
    return GeneratedImage(image=image, cost=units * COST_PER_UNIT_USD)

"""PoC-2 V2 : génération d'image par modèle image natif (Gemini image).

Deux fournisseurs interchangeables derrière la même frontière :
- Fal.ai (Nano Banana 2), utilisé tant que le crédit Fal dure ;
- OpenRouter (google/gemini-3.1-flash-image), repli automatique.

IMAGE_PROVIDER : "auto" (défaut) = Fal si FAL_KEY est définie, avec repli sur
OpenRouter quand Fal refuse pour cause de crédit épuisé ; "fal" ou "openrouter"
forcent un fournisseur sans repli.

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

FAL_BASE_URL = "https://fal.run"
FAL_DEFAULT_MODEL = "fal-ai/nano-banana-2/edit"
ASPECT_RATIO = "3:4"  # portrait, adapté aux photos Vinted
RESOLUTION = "1K"
# Fal ne renvoie pas le prix dans la réponse : estimation d'après la grille
# publique (1K = 0,08 $/image), multipliée par `x-fal-billable-units`.
FAL_COST_PER_UNIT_USD = 0.08
# Statuts Fal traités comme « crédit épuisé / accès refusé » : déclenchent le repli.
FAL_BILLING_STATUSES = (402, 403)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = "google/gemini-3.1-flash-image"

REQUEST_TIMEOUT_SECONDS = 300


class ImageGenerationError(Exception):
    """Erreur lors de la génération d'une image."""


class _BillingError(ImageGenerationError):
    """Le fournisseur refuse faute de crédit : repli possible sur un autre."""


@dataclass
class GeneratedImage:
    image: Image.Image
    cost: float


def _decode(raw: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise ImageGenerationError(f"Image renvoyée illisible : {exc}") from exc


def _generate_fal(prompt, references, http, key) -> GeneratedImage:
    model = os.environ.get("FAL_IMAGE_MODEL") or FAL_DEFAULT_MODEL
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
            f"{FAL_BASE_URL}/{model}",
            headers={"Authorization": f"Key {key}"},
            json=body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ImageGenerationError(f"Appel à Fal échoué : {exc}") from exc

    if response.status_code in FAL_BILLING_STATUSES:
        raise _BillingError(f"Fal : HTTP {response.status_code} — {response.text[:200]}")
    if response.status_code != 200:
        raise ImageGenerationError(f"Fal : HTTP {response.status_code} — {response.text[:200]}")

    try:
        image_url = response.json()["images"][0]["url"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ImageGenerationError("Le modèle n'a renvoyé aucune image.") from exc

    try:
        download = http.get(image_url, timeout=REQUEST_TIMEOUT_SECONDS)
        download.raise_for_status()
    except Exception as exc:
        raise ImageGenerationError(f"Image renvoyée illisible : {exc}") from exc

    units = float(response.headers.get("x-fal-billable-units") or 1.0)
    return GeneratedImage(image=_decode(download.content), cost=units * FAL_COST_PER_UNIT_USD)


def _generate_openrouter(prompt, references, http, key) -> GeneratedImage:
    model = os.environ.get("OPENROUTER_IMAGE_MODEL") or OPENROUTER_DEFAULT_MODEL
    content = [{"type": "text", "text": prompt}] + [
        {"type": "image_url", "image_url": {"url": resize_to_data_url(ref)}}
        for ref in references
    ]
    body = {
        "model": model,
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
        raise ImageGenerationError(f"Appel à OpenRouter échoué : {exc}") from exc

    if response.status_code != 200:
        raise ImageGenerationError(
            f"OpenRouter : HTTP {response.status_code} — {response.text[:200]}"
        )

    payload = response.json()
    try:
        data_url = payload["choices"][0]["message"]["images"][0]["image_url"]["url"]
        raw = base64.b64decode(data_url.split(",", 1)[1])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ImageGenerationError("Le modèle n'a renvoyé aucune image.") from exc

    cost = float((payload.get("usage") or {}).get("cost") or 0.0)
    return GeneratedImage(image=_decode(raw), cost=cost)


def generate_image(
    prompt: str,
    references: list[bytes],
    session: requests.Session | None = None,
    fal_key: str | None = None,
    openrouter_key: str | None = None,
    provider: str | None = None,
) -> GeneratedImage:
    """Envoie `prompt` + `references` (images brutes) au modèle image, renvoie 1 image."""
    http = session or requests.Session()
    fal_key = fal_key or os.environ.get("FAL_KEY")
    openrouter_key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
    chosen = (provider or os.environ.get("IMAGE_PROVIDER") or "auto").lower()

    if chosen not in ("auto", "fal", "openrouter"):
        raise ImageGenerationError(f"IMAGE_PROVIDER inconnu : {chosen!r} (auto, fal, openrouter).")

    if chosen == "fal" or (chosen == "auto" and fal_key):
        if not fal_key:
            raise ImageGenerationError("FAL_KEY manquante dans l'environnement. Voir AGENTS.md.")
        try:
            return _generate_fal(prompt, references, http, fal_key)
        except _BillingError:
            if chosen == "fal" or not openrouter_key:
                raise
            # crédit Fal épuisé : on continue sur OpenRouter

    if not openrouter_key:
        raise ImageGenerationError(
            "Aucun fournisseur image disponible : définir FAL_KEY ou OPENROUTER_API_KEY."
        )
    return _generate_openrouter(prompt, references, http, openrouter_key)

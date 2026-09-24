"""PoC-2 : génération des photos de sortie (segmentation + inpainting + composite).

Frontière testable (seam) : generate_listing_photos(photos, draft) -> list[Image].
Les tests mockent les appels Fal.ai (FalClient.remove_background / .inpaint),
jamais la logique de composite (vérifiée avec de vraies opérations Pillow).
"""

from __future__ import annotations

import io
import os

import requests
from PIL import Image

from images import resize_to_data_url
from listing import ListingDraft

FAL_BASE_URL = "https://fal.run"
SEGMENTATION_MODEL = "fal-ai/bria/background/remove"
INPAINTING_MODEL = "fal-ai/flux-general/inpainting"


class PhotoGenerationError(Exception):
    """Erreur lors de la génération d'une photo de sortie."""


class FalClient:
    """Client HTTP minimal pour les endpoints Fal.ai utilisés par le PoC-2."""

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self._api_key = api_key or os.environ.get("FAL_KEY")
        if not self._api_key:
            raise PhotoGenerationError("FAL_KEY manquante dans l'environnement. Voir .env.example.")
        self._session = session or requests.Session()

    def _run(self, model: str, payload: dict) -> dict:
        response = self._session.post(
            f"{FAL_BASE_URL}/{model}",
            headers={"Authorization": f"Key {self._api_key}"},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _download(self, url: str) -> bytes:
        response = self._session.get(url)
        response.raise_for_status()
        return response.content

    def remove_background(self, photo: bytes) -> bytes:
        result = self._run(SEGMENTATION_MODEL, {"image_url": resize_to_data_url(photo)})
        return self._download(result["image"]["url"])

    def inpaint(self, photo: bytes, mask: bytes, references: list[bytes], prompt: str) -> bytes:
        result = self._run(
            INPAINTING_MODEL,
            {
                "image_url": resize_to_data_url(photo),
                "mask_url": resize_to_data_url(mask),
                "ip_adapter_image_urls": [resize_to_data_url(ref) for ref in references],
                "prompt": prompt,
            },
        )
        return self._download(result["images"][0]["url"])


def _mask_from_alpha(foreground_rgba: bytes) -> bytes:
    """Mask à régénérer (blanc = décor, noir = vêtement à préserver)."""
    foreground = Image.open(io.BytesIO(foreground_rgba)).convert("RGBA")
    alpha = foreground.split()[-1]
    mask = Image.eval(alpha, lambda a: 255 - a)

    buffer = io.BytesIO()
    mask.convert("L").save(buffer, format="PNG")
    return buffer.getvalue()


def _composite(original: bytes, foreground_rgba: bytes, generated_background: bytes) -> Image.Image:
    """Recompose : pixels originaux du vêtement replacés par-dessus le décor généré."""
    base = Image.open(io.BytesIO(original)).convert("RGB")
    foreground = Image.open(io.BytesIO(foreground_rgba)).convert("RGBA").resize(base.size)
    background = Image.open(io.BytesIO(generated_background)).convert("RGB").resize(base.size)

    composite = background.copy()
    composite.paste(foreground, (0, 0), foreground.split()[-1])
    return composite


def generate_listing_photos(
    photos: list[bytes],
    draft: ListingDraft,
    count: int = 3,
    porte_ratio: float = 0.5,
    client: FalClient | None = None,
) -> list[Image.Image]:
    """Génère `count` photos de sortie à partir des photos brutes et du plan (draft).

    Cycle sur les photos d'entrée disponibles (jamais d'angle inventé).
    Sans mannequin_ref, aucune sortie "portée" n'est tentée (repli flatlay).
    """
    if not photos:
        raise ValueError("Au moins une photo est requise.")

    fal_client = client or FalClient()
    porte_count = round(count * porte_ratio) if draft.mannequin_ref else 0

    outputs = []
    for i in range(count):
        source_photo = photos[i % len(photos)]
        is_porte = i < porte_count

        foreground = fal_client.remove_background(source_photo)
        mask = _mask_from_alpha(foreground)

        references = list(draft.decor_refs)
        if is_porte and draft.mannequin_ref:
            references = references + [draft.mannequin_ref]

        style = "mannequin porté, cadré sans visage" if is_porte else "à plat ou sur cintre"
        prompt = f"Décor {draft.mood}, {style}"

        background = fal_client.inpaint(source_photo, mask, references, prompt)
        outputs.append(_composite(source_photo, foreground, background))

    return outputs

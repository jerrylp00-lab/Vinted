"""PoC-1 : génération d'un brouillon de fiche Vinted à partir de photo(s).

Frontière testable (seam) : generate_listing_draft(photos) -> ListingDraft.
Les tests mockent la réponse HTTP d'OpenRouter (client.chat.completions.create),
jamais le contenu du prompt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from openai import OpenAI

from images import MAX_IMAGE_SIDE, resize_to_data_url
from llm_client import (
    DEFAULT_MODEL,
    FALLBACK_MODELS,
    OpenRouterKeyMissing,
    build_openrouter_client,
    resolve_model,
)

SYSTEM_PROMPT = """You are an expert Vinted seller, specialized in writing \
effective, honest product listings.

IMPORTANT: all text you write in "titre", "description", "mood" and \
"questions" must be in French — your buyers are on Vinted.fr. These \
instructions are in English only to help you follow them precisely; your \
output language is always French.

From the photos of a garment provided by the user, you write:
- a short, factual title (garment type, brand if visible, one key feature) ;
- an honest, richly detailed, sales-oriented description of at least 6-8 \
sentences that precisely covers everything visible in the photos:
  - cut and silhouette (straight, fitted, oversized, cropped, A-line...) ;
  - collar/neckline, sleeve, and closure type (zipper, buttons, snaps — \
describe their material and color if visible) ;
  - fabric and its visible qualities (texture, sheen, weight, drape/how it \
falls, weave or knit pattern) ;
  - patterns or prints (describe them precisely — placement, scale, motif — \
never just name them) ;
  - exact colors and shades, including any color-blocking or contrast trims ;
  - construction details (stitching style, topstitching, pockets — count \
and type, lining visible or not, hardware — clasps/buckles/zippers, \
embellishments) ;
  - a graded, honest condition assessment (excellent/very good/good/fair \
condition, with any visible flaw named specifically — pilling, small stain, \
loose thread, faded area — or explicitly "no visible flaws" if genuinely \
pristine).
  Never invent a brand, size, or material that isn't visible — ask a \
question instead ;
- a mood in 2 to 5 French words that captures the item's style.

Only include a question in "questions" when a genuinely missing and \
important piece of information prevents you from writing accurately \
(ambiguous fabric, unclear cut, etc.) — never a low-value question. Maximum \
3 questions. Return an empty array when nothing needs clarifying.

If the user gives feedback or answers your questions, apply it and return \
the complete, updated listing (titre, description, mood, questions), not \
just the changed part.

Respond only with a JSON object matching the requested schema."""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "listing_draft",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "titre": {"type": "string"},
                "description": {"type": "string"},
                "mood": {"type": "string"},
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                },
            },
            "required": ["titre", "description", "mood", "questions"],
            "additionalProperties": False,
        },
    },
}


class ListingError(Exception):
    """Erreur lors de la génération ou du parsing du brouillon de fiche."""


@dataclass
class ListingDraft:
    titre: str
    description: str
    mood: str
    questions: list[str] = field(default_factory=list)
    decor_refs: list[bytes] = field(default_factory=list)
    decor_ref_labels: list[str] = field(default_factory=list)
    mannequin_ref: bytes | None = None


def _build_client(client: OpenAI | None) -> OpenAI:
    try:
        return build_openrouter_client(client)
    except OpenRouterKeyMissing as exc:
        raise ListingError(str(exc)) from exc


def _parse_response(content: str) -> ListingDraft:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[len("json"):]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ListingError(f"Réponse JSON invalide du modèle : {exc}") from exc

    try:
        return ListingDraft(
            titre=data["titre"],
            description=data["description"],
            mood=data["mood"],
            questions=list(data.get("questions", [])),
        )
    except KeyError as exc:
        raise ListingError(f"Champ manquant dans la réponse du modèle : {exc}") from exc


def generate_listing_draft(
    photos: list[bytes],
    history: tuple[dict, ...] = (),
    client: OpenAI | None = None,
    model: str | None = None,
) -> ListingDraft:
    """Génère (ou régénère avec feedback) un brouillon de fiche Vinted.

    photos : images brutes du vêtement (bytes), obligatoires au premier appel.
    history : messages {"role": "user"|"assistant", "content": str} de la
        boucle de feedback, ajoutés après le message contenant les photos.
    """
    if not photos:
        raise ValueError("Au moins une photo est requise.")

    resolved_client = _build_client(client)
    resolved_model = resolve_model(model)

    image_content = [
        {"type": "image_url", "image_url": {"url": resize_to_data_url(photo)}}
        for photo in photos
    ]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Voici les photos du vêtement à mettre en vente."},
                *image_content,
            ],
        },
        *history,
    ]

    try:
        response = resolved_client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            response_format=RESPONSE_SCHEMA,
        )
    except Exception as exc:
        raise ListingError(f"Appel au modèle échoué : {exc}") from exc

    content = response.choices[0].message.content
    if content is None:
        raise ListingError("Réponse vide du modèle.")

    return _parse_response(content)

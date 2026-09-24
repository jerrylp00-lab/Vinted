"""PoC-1 : génération d'un brouillon de fiche Vinted à partir de photo(s).

Frontière testable (seam) : generate_listing_draft(photos) -> ListingDraft.
Les tests mockent la réponse HTTP d'OpenRouter (client.chat.completions.create),
jamais le contenu du prompt.
"""

from __future__ import annotations

import base64
import io
import json
import os
from dataclasses import dataclass, field

from openai import OpenAI
from PIL import Image

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
FALLBACK_MODELS = ["openai/gpt-4o-mini", "anthropic/claude-haiku-4.5"]

MAX_IMAGE_SIDE = 1280

SYSTEM_PROMPT = """Tu es un vendeur Vinted expert, spécialisé dans la rédaction \
de fiches produit efficaces et honnêtes.

À partir des photos d'un vêtement fournies par l'utilisateur, tu rédiges :
- un titre factuel et court (type de vêtement, marque si visible, caractéristique clé) ;
- une description honnête, détaillée et vendeuse d'au moins 4-5 phrases, qui décrit \
précisément tout ce qui est visible sur les photos : coupe et silhouette (droite, \
ajustée, oversize...), type de col/manches/fermeture, matière et son aspect (texture, \
brillance, épaisseur), motifs ou imprimés (les décrire, pas seulement les nommer), \
couleurs exactes et nuances, détails de finition (surpiqûres, boutons, poches, \
liserés, doublure visible), et état réel de la pièce (usure, défauts éventuels, \
signes visibles de très bon état). Ne jamais inventer une marque, une taille ou une \
matière non visible — poser une question à la place ;
- un mood en 2 à 5 mots qui résume le style de l'article.

Tu ne poses une question dans "questions" que si une information réellement \
manquante et importante t'empêche de rédiger correctement (matière ambiguë, \
coupe peu claire, etc.) — jamais de question de confort. Maximum 3 questions. \
Si tu n'as besoin de rien, renvoie un tableau vide.

Si l'utilisateur te donne un retour ou répond à tes questions, applique ce \
retour et renvoie l'annonce complète mise à jour (titre, description, mood, \
questions), pas seulement la partie modifiée.

Réponds uniquement avec un objet JSON respectant le schéma demandé."""

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


def _resize_to_data_url(photo: bytes) -> str:
    image = Image.open(io.BytesIO(photo))
    image = image.convert("RGB")

    width, height = image.size
    longest_side = max(width, height)
    if longest_side > MAX_IMAGE_SIDE:
        scale = MAX_IMAGE_SIDE / longest_side
        image = image.resize((round(width * scale), round(height * scale)))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _build_client(client: OpenAI | None) -> OpenAI:
    if client is not None:
        return client

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ListingError(
            "OPENROUTER_API_KEY manquante dans l'environnement. "
            "Voir .env.example pour la configuration."
        )
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


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
    resolved_model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL

    image_content = [
        {"type": "image_url", "image_url": {"url": _resize_to_data_url(photo)}}
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

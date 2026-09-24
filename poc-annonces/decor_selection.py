"""PoC-2 : sélection des decor_refs et du mannequin de référence.

Filtrage par dossier (genre + type de vêtement, sans coût) puis jugement
visuel réel du LLM sur le sous-ensemble filtré — jamais uniquement sur la
description texte en cache. Le mood du draft est dérivé de ce choix.
"""

from __future__ import annotations

import json
from dataclasses import replace

from images import resize_to_data_url
from library import MANNEQUIN_ROOT, LibraryEntry, download_file
from listing import ListingDraft
from llm_client import OpenRouterKeyMissing, build_openrouter_client, resolve_model

MAX_CANDIDATES = 10

SELECT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "decor_selection",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "chosen_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 3,
                },
                "mood": {"type": "string"},
            },
            "required": ["chosen_indices", "mood"],
            "additionalProperties": False,
        },
    },
}

SELECT_PROMPT = (
    "Voici l'annonce en cours de rédaction et un ensemble de photos de "
    "référence de ma bibliothèque de style (décor/mise en scène, pas le "
    "même vêtement). Choisis 2 à 3 références (par leur index, en partant "
    "de 0) qui conviendraient comme inspiration de décor pour cet article, "
    "et donne un mood en français, en 2 à 5 mots, dérivé de ce choix."
)


class DecorSelectionError(Exception):
    """Erreur lors de la sélection des decor_refs."""


def _filter_candidates(index_entries: list[LibraryEntry], genre: str, type_vetement: str) -> list[LibraryEntry]:
    return [
        entry
        for entry in index_entries
        if not entry.is_mannequin and entry.genre == genre and entry.type_vetement == type_vetement
    ][:MAX_CANDIDATES]


def _pick_mannequin(index_entries: list[LibraryEntry], genre: str) -> LibraryEntry | None:
    candidates = [entry for entry in index_entries if entry.path.startswith(f"{MANNEQUIN_ROOT}/{genre}/")]
    return candidates[0] if candidates else None


def select_decor_refs(
    genre: str,
    type_vetement: str,
    draft: ListingDraft,
    index_entries: list[LibraryEntry],
    service,
    client=None,
    model: str | None = None,
) -> ListingDraft:
    """Choisit 2-3 decor_refs + un mannequin de référence, renvoie un draft enrichi.

    Si la bibliothèque n'a aucune photo pour ce genre/type (dossier encore
    vide), renvoie le draft inchangé plutôt que d'échouer.
    """
    candidates = _filter_candidates(index_entries, genre, type_vetement)
    if not candidates:
        return draft

    try:
        resolved_client = build_openrouter_client(client)
    except OpenRouterKeyMissing as exc:
        raise DecorSelectionError(str(exc)) from exc
    resolved_model = resolve_model(model)

    candidate_photos = [download_file(service, entry.file_id) for entry in candidates]
    image_content = [
        {"type": "image_url", "image_url": {"url": resize_to_data_url(photo)}} for photo in candidate_photos
    ]

    context = f"Titre : {draft.titre}\nDescription : {draft.description}\nMood actuel : {draft.mood}"

    try:
        response = resolved_client.chat.completions.create(
            model=resolved_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{SELECT_PROMPT}\n\n{context}"},
                        *image_content,
                    ],
                }
            ],
            response_format=SELECT_SCHEMA,
        )
    except Exception as exc:
        raise DecorSelectionError(f"Appel au modèle échoué : {exc}") from exc

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        chosen_indices = data["chosen_indices"]
        mood = data["mood"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise DecorSelectionError(f"Réponse invalide du modèle : {exc}") from exc

    decor_refs = [candidate_photos[i] for i in chosen_indices if 0 <= i < len(candidate_photos)]
    decor_ref_labels = [candidates[i].path for i in chosen_indices if 0 <= i < len(candidates)]

    mannequin_entry = _pick_mannequin(index_entries, genre)
    mannequin_ref = download_file(service, mannequin_entry.file_id) if mannequin_entry else None

    return replace(
        draft,
        mood=mood,
        decor_refs=decor_refs,
        decor_ref_labels=decor_ref_labels,
        mannequin_ref=mannequin_ref,
    )

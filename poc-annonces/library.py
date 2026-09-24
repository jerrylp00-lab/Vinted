"""PoC-2 : indexation de la bibliothèque Drive de photos de référence.

Produit decor_index.json (une entrée par photo), lu ensuite par
decor_selection.py plutôt que de ré-analyser toute la bibliothèque en
vision à chaque fiche. Les dossiers `Mannequin/*` sont indexés (chemin +
id) mais jamais décrits en vision (jamais proposés comme decor_refs).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from images import resize_to_data_url
from llm_client import OpenRouterKeyMissing, build_openrouter_client, resolve_model

MANNEQUIN_ROOT = "Mannequin"
IMAGE_MIME_PREFIX = "image/"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

DESCRIBE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "library_entry_description",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["description", "tags"],
            "additionalProperties": False,
        },
    },
}

DESCRIBE_PROMPT = (
    "Décris en une phrase courte le style visuel de cette photo de référence "
    "(décor, ambiance, mise en scène, pose) et donne 2 à 4 tags de style. "
    "Ne décris pas le vêtement lui-même, seulement le décor/l'ambiance."
)


class LibraryError(Exception):
    """Erreur lors de l'accès ou de l'indexation de la bibliothèque Drive."""


@dataclass
class LibraryEntry:
    path: str
    file_id: str
    description: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def is_mannequin(self) -> bool:
        return self.path.startswith(f"{MANNEQUIN_ROOT}/")

    @property
    def genre(self) -> str:
        return self.path.split("/", 1)[0]

    @property
    def type_vetement(self) -> str | None:
        parts = self.path.split("/")
        return parts[1] if len(parts) > 2 else None


def list_children(service, folder_id: str) -> list[dict]:
    query = f"'{folder_id}' in parents and trashed = false"
    response = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    return response.get("files", [])


def download_file(service, file_id: str) -> bytes:
    return service.files().get_media(fileId=file_id).execute()


def walk_library(service, root_folder_id: str) -> list[dict]:
    """Parcourt récursivement la bibliothèque, retourne les fichiers image trouvés.

    Un dossier vide (ex : Homme/ pas encore peuplé) produit simplement
    aucune entrée, sans erreur.
    """
    found = []
    stack = [(root_folder_id, "")]
    while stack:
        folder_id, path = stack.pop()
        for child in list_children(service, folder_id):
            name = child["name"].strip()
            child_path = f"{path}/{name}" if path else name
            if child["mimeType"] == FOLDER_MIME_TYPE:
                stack.append((child["id"], child_path))
            elif child["mimeType"].startswith(IMAGE_MIME_PREFIX):
                found.append({"path": child_path, "id": child["id"]})
    return found


def _describe_photo(photo: bytes, client, model: str) -> tuple[str, list[str]]:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": DESCRIBE_PROMPT},
                    {"type": "image_url", "image_url": {"url": resize_to_data_url(photo)}},
                ],
            }
        ],
        response_format=DESCRIBE_SCHEMA,
    )
    content = response.choices[0].message.content
    data = json.loads(content)
    return data["description"], list(data.get("tags", []))


def index_library(service, root_folder_id: str, client=None, model: str | None = None) -> list[LibraryEntry]:
    """Parcourt la bibliothèque Drive et décrit chaque photo (hors Mannequin/*)."""
    try:
        resolved_client = build_openrouter_client(client)
    except OpenRouterKeyMissing as exc:
        raise LibraryError(str(exc)) from exc
    resolved_model = resolve_model(model)

    entries = []
    for item in walk_library(service, root_folder_id):
        entry = LibraryEntry(path=item["path"], file_id=item["id"])
        if not entry.is_mannequin:
            photo = download_file(service, item["id"])
            entry.description, entry.tags = _describe_photo(photo, resolved_client, resolved_model)
        entries.append(entry)
    return entries


def save_index(entries: list[LibraryEntry], path: str = "decor_index.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(entry) for entry in entries], f, ensure_ascii=False, indent=2)


def load_index(path: str = "decor_index.json") -> list[LibraryEntry]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [LibraryEntry(**item) for item in raw]

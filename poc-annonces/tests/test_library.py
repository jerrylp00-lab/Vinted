"""Tests de l'indexation de la bibliothèque Drive (PoC-2).

Mock au niveau du service Drive (files().list()/.get_media()) et du client
vision (chat.completions.create), jamais de la logique de parcours.
"""

from __future__ import annotations

import io
import json

from PIL import Image

from library import LibraryEntry, index_library, load_index, save_index, walk_library


def _make_photo(color=(10, 20, 30)) -> bytes:
    image = Image.new("RGB", (200, 150), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeMediaRequest:
    def __init__(self, content: bytes):
        self._content = content

    def execute(self):
        return self._content


class FakeFilesResource:
    def __init__(self, tree: dict, contents: dict):
        self._tree = tree
        self._contents = contents
        self._pending_folder_id = None

    def list(self, q, fields):
        self._pending_folder_id = q.split("'")[1]
        return self

    def execute(self):
        return {"files": self._tree.get(self._pending_folder_id, [])}

    def get_media(self, fileId):
        return _FakeMediaRequest(self._contents[fileId])


class FakeDriveService:
    def __init__(self, tree: dict, contents: dict):
        self._files = FakeFilesResource(tree, contents)

    def files(self):
        return self._files


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **kwargs):
        return _FakeResponse(self.content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class FakeVisionClient:
    def __init__(self, content: str):
        self.chat = _FakeChat(content)


def _tree_and_contents():
    tree = {
        "root": [
            {"id": "femme", "name": "Femme", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "homme", "name": "Homme", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "mannequin", "name": "Mannequin", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "femme": [
            {"id": "chaussures", "name": "Chaussures", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "chaussures": [
            {"id": "photo1", "name": "photo1.jpg", "mimeType": "image/jpeg"},
        ],
        "homme": [],
        "mannequin": [
            {"id": "mannequin_femme", "name": "Femme", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "mannequin_femme": [
            {"id": "photo_mannequin", "name": "ref1.jpg", "mimeType": "image/jpeg"},
        ],
    }
    contents = {
        "photo1": _make_photo((10, 20, 30)),
        "photo_mannequin": _make_photo((200, 200, 200)),
    }
    return tree, contents


def test_walk_library_finds_images_and_handles_empty_folders():
    tree, contents = _tree_and_contents()
    service = FakeDriveService(tree, contents)

    found = walk_library(service, "root")
    paths = {item["path"] for item in found}

    assert "Femme/Chaussures/photo1.jpg" in paths
    assert "Mannequin/Femme/ref1.jpg" in paths
    assert len(found) == 2


def test_walk_library_strips_stray_whitespace_in_folder_names():
    tree = {
        "root": [{"id": "mannequin", "name": "Mannequin ", "mimeType": "application/vnd.google-apps.folder"}],
        "mannequin": [{"id": "femme", "name": " Femme", "mimeType": "application/vnd.google-apps.folder"}],
        "femme": [{"id": "photo", "name": "ref.jpg", "mimeType": "image/jpeg"}],
    }
    service = FakeDriveService(tree, {})

    found = walk_library(service, "root")

    assert found == [{"path": "Mannequin/Femme/ref.jpg", "id": "photo"}]


def test_index_library_describes_non_mannequin_photos_only():
    tree, contents = _tree_and_contents()
    service = FakeDriveService(tree, contents)
    vision_content = json.dumps({"description": "Fond blanc studio", "tags": ["minimaliste", "studio"]})
    client = FakeVisionClient(vision_content)

    entries = index_library(service, "root", client=client)
    by_path = {e.path: e for e in entries}

    assert by_path["Femme/Chaussures/photo1.jpg"].description == "Fond blanc studio"
    assert by_path["Femme/Chaussures/photo1.jpg"].tags == ["minimaliste", "studio"]
    assert by_path["Mannequin/Femme/ref1.jpg"].description == ""
    assert by_path["Mannequin/Femme/ref1.jpg"].is_mannequin


def test_save_and_load_index_roundtrip(tmp_path):
    entries = [LibraryEntry(path="Femme/Sac/photo.jpg", file_id="abc", description="desc", tags=["a", "b"])]
    path = tmp_path / "decor_index.json"

    save_index(entries, str(path))
    loaded = load_index(str(path))

    assert loaded == entries

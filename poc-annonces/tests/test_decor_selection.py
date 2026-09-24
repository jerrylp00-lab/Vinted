"""Tests de la sélection des decor_refs et du mannequin (PoC-2).

Mock au niveau du service Drive (download) et du client vision
(chat.completions.create), pas de la logique de filtrage.
"""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from decor_selection import DecorSelectionError, select_decor_refs
from library import LibraryEntry
from listing import ListingDraft


def _make_photo(color=(10, 20, 30)) -> bytes:
    image = Image.new("RGB", (50, 50), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeMediaRequest:
    def __init__(self, content: bytes):
        self._content = content

    def execute(self):
        return self._content


class FakeDriveService:
    def __init__(self, contents: dict):
        self._contents = contents

    def files(self):
        return self

    def get_media(self, fileId):
        return _FakeMediaRequest(self._contents[fileId])


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
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self.content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class FakeClient:
    def __init__(self, content: str):
        self.chat = _FakeChat(content)


def _draft():
    return ListingDraft(titre="Sac cuir", description="Sac en cuir marron.", mood="classique", questions=[])


def _index_entries():
    return [
        LibraryEntry(path="Femme/Sac/ref1.jpg", file_id="ref1"),
        LibraryEntry(path="Femme/Sac/ref2.jpg", file_id="ref2"),
        LibraryEntry(path="Femme/Veste/other.jpg", file_id="other"),
        LibraryEntry(path="Homme/Sac/ref3.jpg", file_id="ref3"),
        LibraryEntry(path="Mannequin/Femme/mref.jpg", file_id="mref"),
    ]


def test_select_decor_refs_filters_by_genre_and_type_and_picks_mannequin():
    img1, img2, mannequin_img = _make_photo((1, 1, 1)), _make_photo((2, 2, 2)), _make_photo((3, 3, 3))
    content = json.dumps({"chosen_indices": [0, 1], "mood": "chic minimaliste"})
    client = FakeClient(content)
    service = FakeDriveService({"ref1": img1, "ref2": img2, "mref": mannequin_img})

    draft = select_decor_refs("Femme", "Sac", _draft(), _index_entries(), service, client=client)

    assert draft.mood == "chic minimaliste"
    assert draft.decor_refs == [img1, img2]
    assert draft.decor_ref_labels == ["Femme/Sac/ref1.jpg", "Femme/Sac/ref2.jpg"]
    assert draft.mannequin_ref == mannequin_img


def test_select_decor_refs_returns_draft_unchanged_when_no_candidates():
    client = FakeClient(json.dumps({"chosen_indices": [], "mood": "x"}))
    service = FakeDriveService({})

    draft = _draft()
    result = select_decor_refs("Homme", "Robe", draft, _index_entries(), service, client=client)

    assert result == draft


def test_select_decor_refs_invalid_json_raises_error():
    client = FakeClient("pas du json")
    service = FakeDriveService({"ref1": _make_photo(), "ref2": _make_photo()})

    with pytest.raises(DecorSelectionError):
        select_decor_refs("Femme", "Sac", _draft(), _index_entries(), service, client=client)


def test_select_decor_refs_no_mannequin_available():
    entries = [entry for entry in _index_entries() if not entry.is_mannequin]
    content = json.dumps({"chosen_indices": [0, 1], "mood": "urbain"})
    client = FakeClient(content)
    service = FakeDriveService({"ref1": _make_photo(), "ref2": _make_photo()})

    draft = select_decor_refs("Femme", "Sac", _draft(), entries, service, client=client)

    assert draft.mannequin_ref is None

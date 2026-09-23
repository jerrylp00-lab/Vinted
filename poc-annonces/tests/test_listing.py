"""Tests du seam PoC-1 : generate_listing_draft(photos) -> ListingDraft.

Mock au niveau de client.chat.completions.create (réponse HTTP OpenRouter),
jamais du contenu du prompt.
"""

from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image

import listing
from listing import ListingDraft, ListingError, generate_listing_draft


def _make_photo(size=(2000, 1500)) -> bytes:
    image = Image.new("RGB", size, color=(120, 200, 80))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self.content)


class FakeChat:
    def __init__(self, content: str):
        self.completions = FakeCompletions(content)


class FakeClient:
    def __init__(self, content: str):
        self.chat = FakeChat(content)


VALID_JSON = json.dumps(
    {
        "titre": "Veste en jean délavée",
        "description": "Veste en jean bleu clair, coupe droite, bon état général.",
        "mood": "casual vintage",
        "questions": ["Quelle est la matière exacte de la doublure ?"],
    }
)


def test_parsing_basic_response():
    client = FakeClient(VALID_JSON)
    draft = generate_listing_draft([_make_photo()], client=client)

    assert draft == ListingDraft(
        titre="Veste en jean délavée",
        description="Veste en jean bleu clair, coupe droite, bon état général.",
        mood="casual vintage",
        questions=["Quelle est la matière exacte de la doublure ?"],
    )


def test_photos_sent_as_resized_data_url():
    client = FakeClient(VALID_JSON)
    generate_listing_draft([_make_photo(size=(2000, 1500))], client=client)

    kwargs = client.chat.completions.last_kwargs
    photo_message = kwargs["messages"][1]
    image_items = [item for item in photo_message["content"] if item["type"] == "image_url"]
    assert len(image_items) == 1

    data_url = image_items[0]["image_url"]["url"]
    assert data_url.startswith("data:image/jpeg;base64,")

    encoded = data_url.split(",", 1)[1]
    decoded_image = Image.open(io.BytesIO(base64.b64decode(encoded)))
    assert max(decoded_image.size) <= listing.MAX_IMAGE_SIDE


def test_multiple_photos_all_included():
    client = FakeClient(VALID_JSON)
    generate_listing_draft([_make_photo(), _make_photo()], client=client)

    kwargs = client.chat.completions.last_kwargs
    photo_message = kwargs["messages"][1]
    image_items = [item for item in photo_message["content"] if item["type"] == "image_url"]
    assert len(image_items) == 2


def test_history_added_after_photos_message():
    client = FakeClient(VALID_JSON)
    history = (
        {"role": "assistant", "content": "Fiche mise à jour."},
        {"role": "user", "content": "Raccourcis la description."},
    )
    generate_listing_draft([_make_photo()], history=history, client=client)

    kwargs = client.chat.completions.last_kwargs
    messages = kwargs["messages"]

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert any(item["type"] == "image_url" for item in messages[1]["content"])
    assert messages[2:] == list(history)


def test_questions_preserved():
    content = json.dumps(
        {
            "titre": "Sac à main cuir",
            "description": "Sac en cuir marron, bon état.",
            "mood": "élégant intemporel",
            "questions": ["Quelle est la marque ?", "Quelles sont les dimensions ?"],
        }
    )
    client = FakeClient(content)
    draft = generate_listing_draft([_make_photo()], client=client)

    assert draft.questions == ["Quelle est la marque ?", "Quelles sont les dimensions ?"]


def test_empty_questions_array():
    content = json.dumps(
        {
            "titre": "Veste en jean délavée",
            "description": "Veste en jean bleu clair, coupe droite, bon état général.",
            "mood": "casual vintage",
            "questions": [],
        }
    )
    client = FakeClient(content)
    draft = generate_listing_draft([_make_photo()], client=client)

    assert draft.questions == []


def test_json_wrapped_in_code_fences():
    fenced = f"```json\n{VALID_JSON}\n```"
    client = FakeClient(fenced)
    draft = generate_listing_draft([_make_photo()], client=client)

    assert draft.titre == "Veste en jean délavée"


def test_invalid_json_raises_listing_error():
    client = FakeClient("ceci n'est pas du JSON")
    with pytest.raises(ListingError):
        generate_listing_draft([_make_photo()], client=client)


def test_missing_field_raises_listing_error():
    incomplete = json.dumps({"titre": "Sac", "description": "Un sac.", "questions": []})
    client = FakeClient(incomplete)
    with pytest.raises(ListingError):
        generate_listing_draft([_make_photo()], client=client)


def test_no_photos_raises_value_error():
    client = FakeClient(VALID_JSON)
    with pytest.raises(ValueError):
        generate_listing_draft([], client=client)


def test_missing_api_key_raises_listing_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ListingError):
        generate_listing_draft([_make_photo()])

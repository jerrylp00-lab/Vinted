# tests/test_image_gen.py
"""Tests du client image OpenRouter. On mocke la session HTTP, jamais le décodage."""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from image_gen import DEFAULT_IMAGE_MODEL, ImageGenerationError, generate_image


def _png(color=(10, 20, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _data_url(color=(10, 20, 30)) -> str:
    return "data:image/png;base64," + base64.b64encode(_png(color)).decode()


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return self.response


def _ok_payload(cost=0.069):
    return {
        "choices": [{"message": {"images": [{"image_url": {"url": _data_url((200, 0, 0))}}]}}],
        "usage": {"cost": cost},
    }


def test_generate_image_decodes_image_and_cost():
    session = FakeSession(FakeResponse(_ok_payload(0.069)))
    result = generate_image("prompt", [_png()], session=session, api_key="k")
    assert result.image.getpixel((0, 0)) == (200, 0, 0)
    assert result.cost == pytest.approx(0.069)


def test_generate_image_sends_text_then_references_with_image_modality():
    session = FakeSession(FakeResponse(_ok_payload()))
    generate_image("mon prompt", [_png(), _png((1, 1, 1))], session=session, api_key="k")
    call = session.calls[0]
    assert call["json"]["model"] == DEFAULT_IMAGE_MODEL
    assert call["json"]["modalities"] == ["image", "text"]
    assert call["json"]["usage"] == {"include": True}
    content = call["json"]["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "mon prompt"}
    assert [part["type"] for part in content[1:]] == ["image_url", "image_url"]
    assert call["headers"]["Authorization"] == "Bearer k"


def test_generate_image_model_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_IMAGE_MODEL", "google/autre-modele")
    session = FakeSession(FakeResponse(_ok_payload()))
    generate_image("p", [_png()], session=session, api_key="k")
    assert session.calls[0]["json"]["model"] == "google/autre-modele"


def test_generate_image_without_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ImageGenerationError, match="OPENROUTER_API_KEY"):
        generate_image("p", [_png()], session=FakeSession(FakeResponse({})))


def test_generate_image_no_image_in_response_raises():
    payload = {"choices": [{"message": {"content": "Je ne peux pas."}}], "usage": {"cost": 0.001}}
    with pytest.raises(ImageGenerationError, match="aucune image"):
        generate_image("p", [_png()], session=FakeSession(FakeResponse(payload)), api_key="k")


def test_generate_image_http_error_raises():
    session = FakeSession(FakeResponse({"error": "quota"}, status_code=429))
    with pytest.raises(ImageGenerationError, match="429"):
        generate_image("p", [_png()], session=session, api_key="k")

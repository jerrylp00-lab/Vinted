"""Tests du client image Fal. On mocke la session HTTP, jamais le décodage."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from image_gen import DEFAULT_IMAGE_MODEL, ImageGenerationError, generate_image


def _png(color=(10, 20, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, payload=None, status_code=200, content=b"", headers=None):
        self._payload = payload
        self.status_code = status_code
        self.content = content
        self.text = str(payload)
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, post_response, download=None):
        self.post_response = post_response
        self.download = download or FakeResponse(content=_png((200, 0, 0)))
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return self.post_response

    def get(self, url, timeout=None):
        self.calls.append({"get": url})
        return self.download


def _ok(units="1.0"):
    return FakeResponse(
        {"images": [{"url": "https://fal.media/x.png"}]},
        headers={"x-fal-billable-units": units},
    )


def test_generate_image_decodes_image_and_estimates_cost():
    result = generate_image("p", [_png()], session=FakeSession(_ok("1.0")), api_key="k")
    assert result.image.getpixel((0, 0)) == (200, 0, 0)
    assert result.cost == pytest.approx(0.08)


def test_generate_image_cost_scales_with_billable_units():
    result = generate_image("p", [_png()], session=FakeSession(_ok("1.5")), api_key="k")
    assert result.cost == pytest.approx(0.12)


def test_generate_image_sends_prompt_and_references_as_image_urls():
    session = FakeSession(_ok())
    generate_image("mon prompt", [_png(), _png((1, 1, 1))], session=session, api_key="k")
    call = session.calls[0]
    assert call["url"].endswith(DEFAULT_IMAGE_MODEL)
    assert call["headers"]["Authorization"] == "Key k"
    assert call["json"]["prompt"] == "mon prompt"
    assert len(call["json"]["image_urls"]) == 2
    assert call["json"]["image_urls"][0].startswith("data:image/jpeg;base64,")
    assert call["json"]["num_images"] == 1
    assert call["json"]["aspect_ratio"] == "3:4"


def test_generate_image_model_from_env(monkeypatch):
    monkeypatch.setenv("FAL_IMAGE_MODEL", "fal-ai/autre/edit")
    session = FakeSession(_ok())
    generate_image("p", [_png()], session=session, api_key="k")
    assert session.calls[0]["url"].endswith("fal-ai/autre/edit")


def test_generate_image_without_key_raises(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(ImageGenerationError, match="FAL_KEY"):
        generate_image("p", [_png()], session=FakeSession(_ok()))


def test_generate_image_no_image_in_response_raises():
    session = FakeSession(FakeResponse({"images": []}))
    with pytest.raises(ImageGenerationError, match="aucune image"):
        generate_image("p", [_png()], session=session, api_key="k")


def test_generate_image_http_error_raises():
    session = FakeSession(FakeResponse({"detail": "quota"}, status_code=429))
    with pytest.raises(ImageGenerationError, match="429"):
        generate_image("p", [_png()], session=session, api_key="k")


def test_generate_image_download_failure_raises():
    session = FakeSession(_ok(), download=FakeResponse(status_code=500))
    with pytest.raises(ImageGenerationError, match="illisible"):
        generate_image("p", [_png()], session=session, api_key="k")

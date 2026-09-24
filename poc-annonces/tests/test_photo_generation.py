"""Tests de la génération des photos de sortie (PoC-2).

Mock les appels Fal.ai (FalClient.remove_background / .inpaint), pas la
logique de composite : la préservation des pixels du vêtement est vérifiée
avec de vraies opérations Pillow sur des images synthétiques.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from listing import ListingDraft
from photo_generation import PhotoGenerationError, generate_listing_photos


def _make_photo(size=(100, 100), color=(255, 0, 0)) -> bytes:
    image = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _make_foreground_rgba(size=(100, 100), fg_color=(255, 0, 0)) -> bytes:
    """Simule un résultat de suppression de fond : carré central opaque, reste transparent."""
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(30, 70):
        for y in range(30, 70):
            image.putpixel((x, y), (*fg_color, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FakeFalClient:
    def __init__(self, foreground: bytes, background_color=(0, 255, 0)):
        self.foreground = foreground
        self.background_color = background_color
        self.inpaint_calls = []

    def remove_background(self, photo: bytes) -> bytes:
        return self.foreground

    def inpaint(self, photo, mask, references, prompt):
        self.inpaint_calls.append({"references": references, "prompt": prompt})
        image = Image.new("RGB", (100, 100), self.background_color)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        return buffer.getvalue()


def _draft(decor_refs=None, mannequin_ref=None):
    return ListingDraft(
        titre="Veste",
        description="Une veste.",
        mood="casual",
        questions=[],
        decor_refs=decor_refs or [b"ref-a", b"ref-b"],
        decor_ref_labels=["a", "b"],
        mannequin_ref=mannequin_ref,
    )


def test_generates_requested_number_of_photos():
    fal = FakeFalClient(_make_foreground_rgba())
    outputs = generate_listing_photos([_make_photo()], _draft(), count=3, client=fal)

    assert len(outputs) == 3


def test_garment_pixels_preserved_in_composite():
    fg_color = (255, 0, 0)
    fal = FakeFalClient(_make_foreground_rgba(fg_color=fg_color), background_color=(0, 255, 0))
    photo = _make_photo(color=fg_color)

    outputs = generate_listing_photos([photo], _draft(), count=1, client=fal)

    result = outputs[0].convert("RGB")
    assert result.getpixel((50, 50)) == fg_color
    assert result.getpixel((5, 5)) != fg_color


def test_mannequin_ref_included_only_for_porte_outputs():
    fal = FakeFalClient(_make_foreground_rgba())
    draft = _draft(mannequin_ref=b"mannequin-bytes")

    generate_listing_photos([_make_photo()], draft, count=4, porte_ratio=0.5, client=fal)

    porte_calls = fal.inpaint_calls[:2]
    flatlay_calls = fal.inpaint_calls[2:]

    assert all(b"mannequin-bytes" in call["references"] for call in porte_calls)
    assert all(b"mannequin-bytes" not in call["references"] for call in flatlay_calls)


def test_no_mannequin_falls_back_to_flatlay_only():
    fal = FakeFalClient(_make_foreground_rgba())
    draft = _draft(mannequin_ref=None)

    generate_listing_photos([_make_photo()], draft, count=2, porte_ratio=1.0, client=fal)

    assert all(b"mannequin-bytes" not in call["references"] for call in fal.inpaint_calls)


def test_missing_angle_reuses_available_photos_not_invented():
    fal = FakeFalClient(_make_foreground_rgba())
    photo_a = _make_photo(color=(1, 1, 1))
    photo_b = _make_photo(color=(2, 2, 2))

    outputs = generate_listing_photos([photo_a, photo_b], _draft(), count=3, client=fal)

    assert len(outputs) == 3


def test_no_photos_raises_value_error():
    fal = FakeFalClient(_make_foreground_rgba())
    with pytest.raises(ValueError):
        generate_listing_photos([], _draft(), client=fal)


def test_missing_fal_key_raises_error(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(PhotoGenerationError):
        generate_listing_photos([_make_photo()], _draft())

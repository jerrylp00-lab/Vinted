# tests/test_photo_generation.py
"""Tests de l'orchestration PoC-2 V2. On injecte les générateurs (frontière HTTP)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from fidelity import FidelityError, FidelityVerdict
from image_gen import GeneratedImage, ImageGenerationError
from listing import ListingDraft
from photo_generation import generate_listing_photos, generate_shot
from shots import SHOTS, SHOTS_BY_ID

MANNEQUIN = b"MANNEQUIN-BYTES"


def _png(color=(120, 120, 120)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _draft(mannequin=True) -> ListingDraft:
    return ListingDraft(
        titre="T-shirt",
        description="d",
        mood="rétro",
        decor_refs=[_png((1, 1, 1)), _png((2, 2, 2))],
        mannequin_ref=MANNEQUIN if mannequin else None,
    )


class FakeGenerator:
    def __init__(self, cost=0.07, fail_when=None):
        self.calls = []
        self.cost = cost
        self.fail_when = fail_when

    def __call__(self, prompt, references, **kwargs):
        self.calls.append({"prompt": prompt, "references": references})
        if self.fail_when and self.fail_when in prompt:
            raise ImageGenerationError("quota dépassé")
        return GeneratedImage(image=Image.new("RGB", (8, 8), (50, 60, 70)), cost=self.cost)


def _always_ok(originals, generated, **kwargs):
    return FidelityVerdict(ok=True, problemes=[], cost=0.001)


def _always_drift(originals, generated, **kwargs):
    return FidelityVerdict(ok=False, problemes=["logo différent"], cost=0.001)


def test_generates_four_results_in_shot_order_with_summed_cost():
    generator = FakeGenerator(cost=0.07)
    results = generate_listing_photos(
        [_png()], _draft(), image_generator=generator, fidelity_checker=_always_ok
    )
    assert [r.shot_id for r in results] == [s.id for s in SHOTS]
    assert all(r.image is not None and r.error is None for r in results)
    assert all(r.cost == pytest.approx(0.071) for r in results)
    assert len(generator.calls) == 4


def test_mannequin_sent_only_on_porte_shot():
    generator = FakeGenerator()
    generate_listing_photos(
        [_png()], _draft(), image_generator=generator, fidelity_checker=_always_ok
    )
    with_mannequin = [c for c in generator.calls if MANNEQUIN in c["references"]]
    assert len(with_mannequin) == 1
    assert "mirror selfie" in with_mannequin[0]["prompt"]


def test_one_failing_shot_does_not_stop_the_others():
    generator = FakeGenerator(fail_when="Very close-up")
    results = generate_listing_photos(
        [_png()], _draft(), image_generator=generator, fidelity_checker=_always_ok
    )
    by_id = {r.shot_id: r for r in results}
    assert by_id["detail"].image is None
    assert "quota dépassé" in by_id["detail"].error
    assert all(by_id[i].image is not None for i in ("porte_miroir", "a_plat", "cintre"))


def test_drift_triggers_exactly_one_retry_then_flags():
    generator = FakeGenerator(cost=0.07)
    result = generate_shot(
        [_png()], _draft(), SHOTS_BY_ID["a_plat"],
        image_generator=generator, fidelity_checker=_always_drift,
    )
    assert result.attempts == 2
    assert len(generator.calls) == 2
    assert result.image is not None
    assert result.verdict.ok is False
    assert result.cost == pytest.approx(2 * (0.07 + 0.001))
    assert "logo différent" in generator.calls[1]["prompt"]  # le retry corrige la dérive


def test_no_retry_when_faithful():
    generator = FakeGenerator()
    result = generate_shot(
        [_png()], _draft(), SHOTS_BY_ID["a_plat"],
        image_generator=generator, fidelity_checker=_always_ok,
    )
    assert result.attempts == 1
    assert result.verdict.ok is True


def test_fidelity_check_failure_keeps_image_without_verdict():
    def broken_checker(originals, generated, **kwargs):
        raise FidelityError("panne")

    result = generate_shot(
        [_png()], _draft(), SHOTS_BY_ID["cintre"],
        image_generator=FakeGenerator(), fidelity_checker=broken_checker,
    )
    assert result.image is not None
    assert result.verdict is None
    assert result.attempts == 1


def test_retry_failure_keeps_first_image():
    calls = {"n": 0}

    def flaky(prompt, references, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ImageGenerationError("filtre")
        return GeneratedImage(image=Image.new("RGB", (8, 8)), cost=0.07)

    result = generate_shot(
        [_png()], _draft(), SHOTS_BY_ID["cintre"],
        image_generator=flaky, fidelity_checker=_always_drift,
    )
    assert result.image is not None
    assert result.verdict.ok is False
    assert result.error is None


def test_seller_feedback_reaches_the_prompt():
    generator = FakeGenerator()
    generate_shot(
        [_png()], _draft(), SHOTS_BY_ID["detail"], feedback="plus lumineux",
        image_generator=generator, fidelity_checker=_always_ok,
    )
    assert "plus lumineux" in generator.calls[0]["prompt"]


def test_requires_at_least_one_photo():
    with pytest.raises(ValueError):
        generate_listing_photos([], _draft(), image_generator=FakeGenerator())

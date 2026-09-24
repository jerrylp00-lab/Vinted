# tests/test_fidelity.py
from __future__ import annotations

import io
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PIL import Image

from fidelity import FidelityError, check_fidelity


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (5, 5, 5)).save(buffer, format="PNG")
    return buffer.getvalue()


def _client(content, cost=0.0012):
    create = MagicMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(cost=cost),
        )
    )
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), create


def _generated() -> Image.Image:
    return Image.new("RGB", (8, 8), (9, 9, 9))


def test_ok_verdict():
    client, _ = _client(json.dumps({"ok": True, "problemes": []}))
    verdict = check_fidelity([_png()], _generated(), client=client)
    assert verdict.ok is True
    assert verdict.problemes == []
    assert verdict.cost == pytest.approx(0.0012)


def test_drift_verdict_lists_problems():
    client, _ = _client(json.dumps({"ok": False, "problemes": ["logo différent", "liseré manquant"]}))
    verdict = check_fidelity([_png()], _generated(), client=client)
    assert verdict.ok is False
    assert verdict.problemes == ["logo différent", "liseré manquant"]


def test_sends_originals_then_generated_image():
    client, create = _client(json.dumps({"ok": True, "problemes": []}))
    check_fidelity([_png(), _png()], _generated(), client=client)
    content = create.call_args.kwargs["messages"][1]["content"]
    assert [part["type"] for part in content] == ["text", "image_url", "image_url", "image_url"]
    assert create.call_args.kwargs["extra_body"] == {"usage": {"include": True}}


def test_invalid_json_raises():
    client, _ = _client("pas du json")
    with pytest.raises(FidelityError):
        check_fidelity([_png()], _generated(), client=client)


def test_call_failure_raises():
    create = MagicMock(side_effect=RuntimeError("boom"))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with pytest.raises(FidelityError, match="boom"):
        check_fidelity([_png()], _generated(), client=client)

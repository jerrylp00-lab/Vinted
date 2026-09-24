# PoC-2 V2 — génération photo native : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer le pipeline PoC-2 (Fal.ai segmentation + inpainting + composite) par 4 appels à un modèle image natif (Gemini via OpenRouter), avec briefs par plan, check de fidélité vision et galerie de relecture.

**Architecture:** `shots.py` porte le harnais (briefs par plan + assemblage des références). `image_gen.py` est un client OpenRouter fin (N images en entrée, 1 en sortie, coût remonté). `fidelity.py` compare original et sortie via un LLM vision. `photo_generation.py` orchestre les 4 plans en parallèle avec 1 retry sur dérive. `app.py` affiche une galerie (garder / régénérer avec consigne).

**Tech Stack:** Python 3.13, requests, openai SDK (client OpenRouter existant `llm_client.py`), Pillow, Streamlit, pytest.

Spec : `specs/2026-09-24-poc2-v2-generation-native-design.md`. Spike validé : `google/gemini-3.1-flash-image`, ~0,069 $/image, 11-14 s, image renvoyée dans `choices[0].message.images[0].image_url.url` (data URL base64) avec `modalities: ["image","text"]` et `usage: {"include": true}`.

## Global Constraints

- Tous les commandes depuis `poc-annonces/`. Tests : `pytest tests/ -v`, aucune clé API requise (tout mocké).
- Modèle image : `google/gemini-3.1-flash-image` par défaut, surchargeable par `OPENROUTER_IMAGE_MODEL`. Clé : `OPENROUTER_API_KEY` (aucune nouvelle clé).
- 4 plans fixes, ids : `porte_miroir`, `a_plat`, `cintre`, `detail`, dans cet ordre.
- 4 appels séparés (un par plan), jamais de collage.
- Le mannequin n'est envoyé que sur le plan `porte_miroir`.
- Check de fidélité jamais bloquant : 1 retry automatique max, puis flag ; une panne du check ne perd pas l'image.
- Prompts du harnais en anglais (convention du repo : `listing.py`), sortie visuelle sans texte.
- Pas de dépendance ajoutée (`requests`, `pillow`, `openai` déjà dans `requirements.txt`).
- Commits : message en français préfixé `poc-annonces:`, terminé par `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

## File Structure

| Fichier | Action | Responsabilité |
|---|---|---|
| `image_gen.py` | Créer | Client OpenRouter image : `generate_image(...) -> GeneratedImage` |
| `shots.py` | Créer | Les 4 plans, `build_prompt`, `collect_references` |
| `fidelity.py` | Créer | `check_fidelity(...) -> FidelityVerdict` |
| `photo_generation.py` | Réécrire | `generate_shot`, `generate_listing_photos` → `list[ShotResult]` |
| `app.py` | Modifier | Galerie, régénération par plan, coût |
| `tests/test_image_gen.py`, `test_shots.py`, `test_fidelity.py` | Créer | |
| `tests/test_photo_generation.py` | Réécrire | |
| `AGENTS.md`, `specs/…-design.md` | Modifier | Seam, `.env`, fallback mannequin |

---

### Task 1: Client image OpenRouter (`image_gen.py`)

**Files:**
- Create: `image_gen.py`
- Test: `tests/test_image_gen.py`

**Interfaces:**
- Consumes: `images.resize_to_data_url(photo: bytes) -> str` (existant).
- Produces:
  - `ImageGenerationError(Exception)`
  - `@dataclass GeneratedImage: image: PIL.Image.Image; cost: float`
  - `generate_image(prompt: str, references: list[bytes], model: str | None = None, session: requests.Session | None = None, api_key: str | None = None) -> GeneratedImage`
  - `DEFAULT_IMAGE_MODEL = "google/gemini-3.1-flash-image"`

- [ ] **Step 1: Écrire les tests qui échouent**

```python
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
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `pytest tests/test_image_gen.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'image_gen'`)

- [ ] **Step 3: Implémenter**

```python
# image_gen.py
"""PoC-2 V2 : génération d'image par modèle image natif, via OpenRouter.

Frontière testable : generate_image(prompt, references) -> GeneratedImage.
Les tests mockent la session HTTP (requests), jamais le décodage de l'image.
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass

import requests
from PIL import Image

from images import resize_to_data_url

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_IMAGE_MODEL = "google/gemini-3.1-flash-image"
REQUEST_TIMEOUT_SECONDS = 300


class ImageGenerationError(Exception):
    """Erreur lors de la génération d'une image."""


@dataclass
class GeneratedImage:
    image: Image.Image
    cost: float


def generate_image(
    prompt: str,
    references: list[bytes],
    model: str | None = None,
    session: requests.Session | None = None,
    api_key: str | None = None,
) -> GeneratedImage:
    """Envoie `prompt` + `references` (images brutes) au modèle image, renvoie 1 image."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ImageGenerationError(
            "OPENROUTER_API_KEY manquante dans l'environnement. Voir .env.example."
        )
    resolved_model = model or os.environ.get("OPENROUTER_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL
    http = session or requests.Session()

    content = [{"type": "text", "text": prompt}] + [
        {"type": "image_url", "image_url": {"url": resize_to_data_url(ref)}}
        for ref in references
    ]
    body = {
        "model": resolved_model,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": content}],
        "usage": {"include": True},
    }

    try:
        response = http.post(
            OPENROUTER_CHAT_URL,
            headers={"Authorization": f"Bearer {key}"},
            json=body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ImageGenerationError(f"Appel au modèle image échoué : {exc}") from exc

    if response.status_code != 200:
        raise ImageGenerationError(
            f"Modèle image : HTTP {response.status_code} — {response.text[:200]}"
        )

    payload = response.json()
    try:
        data_url = payload["choices"][0]["message"]["images"][0]["image_url"]["url"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ImageGenerationError("Le modèle n'a renvoyé aucune image.") from exc

    try:
        raw = base64.b64decode(data_url.split(",", 1)[1])
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise ImageGenerationError(f"Image renvoyée illisible : {exc}") from exc

    cost = float((payload.get("usage") or {}).get("cost") or 0.0)
    return GeneratedImage(image=image, cost=cost)
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `pytest tests/test_image_gen.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add image_gen.py tests/test_image_gen.py
git commit -m "poc-annonces: client image OpenRouter (Gemini image natif)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Le harnais des 4 plans (`shots.py`)

**Files:**
- Create: `shots.py`
- Test: `tests/test_shots.py`

**Interfaces:**
- Consumes: `listing.ListingDraft` (champs `mood: str`, `decor_refs: list[bytes]`, `mannequin_ref: bytes | None`).
- Produces:
  - `@dataclass(frozen=True) Shot: id: str; label: str; brief: str; uses_mannequin: bool`
  - `SHOTS: tuple[Shot, ...]` (ids `porte_miroir`, `a_plat`, `cintre`, `detail`, dans cet ordre)
  - `SHOTS_BY_ID: dict[str, Shot]`
  - `collect_references(shot: Shot, photos: list[bytes], draft: ListingDraft) -> list[bytes]` — ordre : photos vêtement, `decor_refs`, mannequin (si `shot.uses_mannequin` et présent)
  - `build_prompt(shot: Shot, draft: ListingDraft, n_garment: int, feedback: str | None = None) -> str`

- [ ] **Step 1: Écrire les tests qui échouent**

```python
# tests/test_shots.py
from __future__ import annotations

from listing import ListingDraft
from shots import SHOTS, SHOTS_BY_ID, build_prompt, collect_references


def _draft(mannequin=b"MANNEQUIN", decor=(b"D1", b"D2")):
    return ListingDraft(
        titre="T-shirt",
        description="d",
        mood="rétro pinup",
        decor_refs=list(decor),
        mannequin_ref=mannequin,
    )


def test_four_fixed_shots_in_order():
    assert [s.id for s in SHOTS] == ["porte_miroir", "a_plat", "cintre", "detail"]
    assert set(SHOTS_BY_ID) == {s.id for s in SHOTS}


def test_only_porte_uses_mannequin():
    assert [s.id for s in SHOTS if s.uses_mannequin] == ["porte_miroir"]


def test_collect_references_order_and_mannequin_only_on_porte():
    photos = [b"P1", b"P2"]
    porte = collect_references(SHOTS_BY_ID["porte_miroir"], photos, _draft())
    assert porte == [b"P1", b"P2", b"D1", b"D2", b"MANNEQUIN"]
    flat = collect_references(SHOTS_BY_ID["a_plat"], photos, _draft())
    assert flat == [b"P1", b"P2", b"D1", b"D2"]


def test_collect_references_without_mannequin():
    porte = collect_references(SHOTS_BY_ID["porte_miroir"], [b"P1"], _draft(mannequin=None))
    assert porte == [b"P1", b"D1", b"D2"]


def test_prompt_states_reference_roles_mood_and_shot_brief():
    prompt = build_prompt(SHOTS_BY_ID["porte_miroir"], _draft(), n_garment=3)
    assert "first 3 attached image" in prompt
    assert "next 2 image" in prompt  # decor_refs
    assert "house model" in prompt
    assert "rétro pinup" in prompt
    assert "mirror selfie" in prompt
    assert "Reproduce the garment EXACTLY" in prompt


def test_prompt_omits_mannequin_and_decor_sections_when_absent():
    prompt = build_prompt(
        SHOTS_BY_ID["a_plat"], _draft(mannequin=None, decor=()), n_garment=1
    )
    assert "house model" not in prompt
    assert "style references" not in prompt


def test_prompt_mannequin_section_only_for_mannequin_shot():
    prompt = build_prompt(SHOTS_BY_ID["cintre"], _draft(), n_garment=1)
    assert "house model" not in prompt


def test_prompt_appends_feedback():
    prompt = build_prompt(SHOTS_BY_ID["detail"], _draft(), n_garment=1, feedback="plus lumineux")
    assert "plus lumineux" in prompt
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `pytest tests/test_shots.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'shots'`)

- [ ] **Step 3: Implémenter**

```python
# shots.py
"""PoC-2 V2 : le harnais — les 4 plans de photo et l'assemblage du prompt.

C'est ici que vit la direction artistique. Contenu des briefs repris du prompt
Gemini validé par l'utilisateur (Test_humain/Gemini/Input/PROMPT.rtf) et
confirmé par le spike du 2026-09-24.
"""

from __future__ import annotations

from dataclasses import dataclass

from listing import ListingDraft

COMMON_BRIEF = (
    "Act as a professional fashion photographer specialized in Parisian "
    "'effortless chic' and UGC (user generated content) aesthetics. "
    "Realistic high-end second-hand look, like a fashion influencer or a luxury "
    "thrift shop: smartphone or 35mm film photo, natural light, soft shadows, "
    "slight grain. No 3D, no CGI, no sterile white-background studio look. "
    "The garment must have a natural, non-rigid drape. "
    "Reproduce the garment EXACTLY as in the attached photos: colour, print, "
    "text, trims, cut and fabric. Invent no detail. "
    "Generate exactly ONE image. Do not add any text or watermark."
)


@dataclass(frozen=True)
class Shot:
    id: str
    label: str
    brief: str
    uses_mannequin: bool = False


SHOTS: tuple[Shot, ...] = (
    Shot(
        id="porte_miroir",
        label="Porté — selfie miroir",
        brief=(
            "The garment worn by a person of average build. Mirror selfie framing; "
            "the face is completely hidden by the smartphone. Background: chic "
            "vintage Parisian apartment, wooden parquet floor, natural light from a window."
        ),
        uses_mannequin=True,
    ),
    Shot(
        id="a_plat",
        label="À plat",
        brief=(
            "The garment laid flat, casually draped (slightly rumpled, not perfectly "
            "ironed), on a vintage textured surface (old parquet floor or Persian rug). "
            "Soft natural light creating realistic shadows."
        ),
    ),
    Shot(
        id="cintre",
        label="Sur cintre",
        brief=(
            "The garment hanging on a wooden hanger, on an off-white wall with light "
            "mouldings. Slightly blurred background: a metal clothes rack with a few "
            "garments, or a vintage chair."
        ),
    ),
    Shot(
        id="detail",
        label="Détail",
        brief=(
            "Very close-up on the garment, casually held by a hand. Sharp focus on "
            "the fabric texture and details (buttons, seams, trims, label). Direct "
            "natural light with slight contrast. Raw, authentic rendering."
        ),
    ),
)

SHOTS_BY_ID: dict[str, Shot] = {shot.id: shot for shot in SHOTS}


def collect_references(shot: Shot, photos: list[bytes], draft: ListingDraft) -> list[bytes]:
    """Images envoyées au modèle : photos du vêtement, decor_refs, puis mannequin si porté."""
    references = [*photos, *draft.decor_refs]
    if shot.uses_mannequin and draft.mannequin_ref:
        references.append(draft.mannequin_ref)
    return references


def build_prompt(
    shot: Shot,
    draft: ListingDraft,
    n_garment: int,
    feedback: str | None = None,
) -> str:
    """Assemble le brief complet. L'ordre décrit doit suivre `collect_references`."""
    parts = [
        COMMON_BRIEF,
        f"The first {n_garment} attached image(s) show ONE garment (different angles): "
        "this is the item to reproduce exactly.",
    ]
    if draft.decor_refs:
        parts.append(
            f"The next {len(draft.decor_refs)} image(s) are style references: take "
            "inspiration from their mood, light and decor only. Do not copy their room, "
            "and ignore any garment or person they show."
        )
    if shot.uses_mannequin and draft.mannequin_ref:
        parts.append(
            "The last image is the house model reference: keep the same build and "
            "silhouette. The face must stay hidden."
        )
    parts.append(f"Overall mood: {draft.mood}.")
    parts.append(f"SHOT: {shot.brief}")
    if feedback:
        parts.append(f"Extra instructions from the seller (they take priority): {feedback}")
    return "\n\n".join(parts)
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `pytest tests/test_shots.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add shots.py tests/test_shots.py
git commit -m "poc-annonces: harnais des 4 plans (briefs + assemblage des références)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Check de fidélité (`fidelity.py`)

**Files:**
- Create: `fidelity.py`
- Test: `tests/test_fidelity.py`

**Interfaces:**
- Consumes: `llm_client.build_openrouter_client`, `llm_client.resolve_model`, `llm_client.OpenRouterKeyMissing`; `images.resize_to_data_url`.
- Produces:
  - `FidelityError(Exception)`
  - `@dataclass FidelityVerdict: ok: bool; problemes: list[str]; cost: float = 0.0`
  - `check_fidelity(originals: list[bytes], generated: PIL.Image.Image, client: OpenAI | None = None, model: str | None = None) -> FidelityVerdict`

- [ ] **Step 1: Écrire les tests qui échouent**

```python
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
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `pytest tests/test_fidelity.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'fidelity'`)

- [ ] **Step 3: Implémenter**

```python
# fidelity.py
"""PoC-2 V2 : check de fidélité — compare le vêtement original à la photo générée.

Filet de sécurité, jamais un blocage : l'appelant traite FidelityError comme
« pas de verdict » et garde l'image.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field

from openai import OpenAI
from PIL import Image

from images import resize_to_data_url
from llm_client import OpenRouterKeyMissing, build_openrouter_client, resolve_model

SYSTEM_PROMPT = """You compare a real garment with an AI-generated photo that \
is supposed to show the same garment in a new setting.

The first images are the real garment (reference). The LAST image is the \
generated photo. Decide whether the garment in the generated photo is faithful \
to the real one: same colours, same print/graphic and any text, same trims and \
piping, same cut and neckline, same fabric look. Ignore differences in \
background, lighting, pose and photo angle. A missing, altered, invented or \
distorted garment detail is a problem.

Write each problem in French, short and specific. Respond only with the JSON \
object requested."""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "fidelity_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "problemes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["ok", "problemes"],
            "additionalProperties": False,
        },
    },
}


class FidelityError(Exception):
    """Le check de fidélité n'a pas pu produire de verdict."""


@dataclass
class FidelityVerdict:
    ok: bool
    problemes: list[str] = field(default_factory=list)
    cost: float = 0.0


def _image_to_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG")
    return buffer.getvalue()


def check_fidelity(
    originals: list[bytes],
    generated: Image.Image,
    client: OpenAI | None = None,
    model: str | None = None,
) -> FidelityVerdict:
    try:
        resolved_client = build_openrouter_client(client)
    except OpenRouterKeyMissing as exc:
        raise FidelityError(str(exc)) from exc

    images = [*originals, _image_to_bytes(generated)]
    content = [{"type": "text", "text": "Reference garment photos, then the generated photo last."}]
    content += [
        {"type": "image_url", "image_url": {"url": resize_to_data_url(img)}} for img in images
    ]

    try:
        response = resolved_client.chat.completions.create(
            model=resolve_model(model),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            response_format=RESPONSE_SCHEMA,
            extra_body={"usage": {"include": True}},
        )
    except Exception as exc:
        raise FidelityError(f"Appel de vérification échoué : {exc}") from exc

    try:
        data = json.loads(response.choices[0].message.content)
        return FidelityVerdict(
            ok=bool(data["ok"]),
            problemes=list(data["problemes"]),
            cost=float(getattr(response.usage, "cost", 0.0) or 0.0),
        )
    except (TypeError, KeyError, ValueError) as exc:
        raise FidelityError(f"Verdict illisible : {exc}") from exc
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `pytest tests/test_fidelity.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add fidelity.py tests/test_fidelity.py
git commit -m "poc-annonces: check de fidélité vision (original vs photo générée)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Orchestration (`photo_generation.py`) et suppression du pipeline Fal

**Files:**
- Rewrite: `photo_generation.py`
- Rewrite: `tests/test_photo_generation.py`

**Interfaces:**
- Consumes: `image_gen.generate_image`, `image_gen.ImageGenerationError`, `image_gen.GeneratedImage`; `shots.SHOTS`, `shots.Shot`, `shots.build_prompt`, `shots.collect_references`; `fidelity.check_fidelity`, `fidelity.FidelityError`, `fidelity.FidelityVerdict`; `listing.ListingDraft`.
- Produces:
  - `@dataclass ShotResult: shot_id: str; label: str; image: PIL.Image.Image | None; error: str | None; verdict: FidelityVerdict | None; cost: float; attempts: int`
  - `generate_shot(photos: list[bytes], draft: ListingDraft, shot: Shot, feedback: str | None = None, image_generator=generate_image, fidelity_checker=check_fidelity) -> ShotResult`
  - `generate_listing_photos(photos: list[bytes], draft: ListingDraft, image_generator=generate_image, fidelity_checker=check_fidelity) -> list[ShotResult]` (un résultat par plan, ordre de `SHOTS`)
  - `MAX_ATTEMPTS = 2`

- [ ] **Step 1: Écrire les tests (remplace tout le fichier)**

```python
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
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `pytest tests/test_photo_generation.py -v`
Expected: FAIL (`ImportError: cannot import name 'generate_shot'`)

- [ ] **Step 3: Réécrire `photo_generation.py`**

```python
"""PoC-2 V2 : génération des photos de sortie par modèle image natif.

Frontière testable (seam) : generate_listing_photos(photos, draft) -> list[ShotResult].
Les tests injectent `image_generator` / `fidelity_checker` (frontière HTTP),
jamais la construction des prompts (shots.py).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from PIL import Image

from fidelity import FidelityError, FidelityVerdict, check_fidelity
from image_gen import ImageGenerationError, generate_image
from listing import ListingDraft
from shots import SHOTS, Shot, build_prompt, collect_references

MAX_ATTEMPTS = 2


@dataclass
class ShotResult:
    shot_id: str
    label: str
    image: Image.Image | None
    error: str | None
    verdict: FidelityVerdict | None
    cost: float
    attempts: int


def generate_shot(
    photos: list[bytes],
    draft: ListingDraft,
    shot: Shot,
    feedback: str | None = None,
    image_generator=generate_image,
    fidelity_checker=check_fidelity,
) -> ShotResult:
    """Génère un plan, le vérifie, retente 1 fois en cas de dérive. Ne lève jamais."""
    references = collect_references(shot, photos, draft)
    cost = 0.0
    image: Image.Image | None = None
    verdict: FidelityVerdict | None = None
    attempt_feedback = feedback
    attempts = 0

    while attempts < MAX_ATTEMPTS:
        attempts += 1
        prompt = build_prompt(shot, draft, n_garment=len(photos), feedback=attempt_feedback)
        try:
            generated = image_generator(prompt, references)
        except ImageGenerationError as exc:
            if image is None:
                return ShotResult(shot.id, shot.label, None, str(exc), None, cost, attempts)
            break  # retry raté : on garde la première image, déjà flaggée

        cost += generated.cost
        image = generated.image

        try:
            verdict = fidelity_checker(photos, image)
        except FidelityError:
            verdict = None
            break
        cost += verdict.cost

        if verdict.ok:
            break
        problems = "; ".join(verdict.problemes)
        attempt_feedback = (
            f"{feedback + ' ' if feedback else ''}"
            f"Previous attempt was not faithful to the garment: {problems}. Fix this."
        )

    return ShotResult(shot.id, shot.label, image, None, verdict, cost, attempts)


def generate_listing_photos(
    photos: list[bytes],
    draft: ListingDraft,
    image_generator=generate_image,
    fidelity_checker=check_fidelity,
) -> list[ShotResult]:
    """Génère les 4 plans en parallèle, un résultat par plan dans l'ordre de SHOTS."""
    if not photos:
        raise ValueError("Au moins une photo est requise.")

    with ThreadPoolExecutor(max_workers=len(SHOTS)) as executor:
        futures = [
            executor.submit(
                generate_shot, photos, draft, shot,
                image_generator=image_generator, fidelity_checker=fidelity_checker,
            )
            for shot in SHOTS
        ]
        return [future.result() for future in futures]
```

- [ ] **Step 4: Lancer toute la suite**

Run: `pytest tests/ -v`
Expected: tout passe (les anciens tests `test_photo_generation` sont remplacés ; `test_decor_selection`, `test_library`, `test_listing` inchangés). Si `app.py` importe encore `PhotoGenerationError`, ce n'est pas testé ici : corrigé à la Task 5.

- [ ] **Step 5: Commit**

```bash
git add photo_generation.py tests/test_photo_generation.py
git commit -m "poc-annonces: orchestration 4 plans avec retry fidélité, retrait du pipeline Fal" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Galerie Streamlit, docs et nettoyage Fal

**Files:**
- Modify: `app.py` (import ligne 18 ; bloc « Style et photos » lignes ~112-146)
- Modify: `AGENTS.md` (seam ligne 12 ; bloc `.env` ligne 39)
- Modify: `specs/2026-09-24-poc2-v2-generation-native-design.md` (cas limite mannequin)

**Interfaces:**
- Consumes: `photo_generation.generate_listing_photos`, `photo_generation.generate_shot`, `photo_generation.ShotResult`; `shots.SHOTS_BY_ID`.
- Produces: rien de consommé ailleurs (couche UI).

- [ ] **Step 1: Mettre à jour les imports de `app.py`**

Remplacer

```python
from photo_generation import PhotoGenerationError, generate_listing_photos
```

par

```python
from photo_generation import generate_listing_photos, generate_shot
from shots import SHOTS_BY_ID
```

Ajouter dans l'init du `session_state` (avec les autres `if "..." not in st.session_state`) :

```python
if "spent" not in st.session_state:
    st.session_state.spent = 0.0
```

et dans le bouton « Nouvelle fiche », ajouter `st.session_state.spent = 0.0`.

- [ ] **Step 2: Remplacer le bloc de génération**

Remplacer tout ce qui suit `st.write(f"Références choisies : ...")` / `st.caption(f"Mood affiné...")` jusqu'à la fin du fichier (le `number_input`, le `slider`, le `st.info` Fal, le bouton et `st.image`) par :

```python
        if st.session_state.draft.mannequin_ref is None:
            st.info(
                "Pas de mannequin maison pour ce genre : le plan porté utilisera "
                "une personne générée librement."
            )
        st.info(
            "La génération appelle un modèle image (~0,07 $/photo, 4 photos + "
            "vérification). Valide seulement quand tu es prêt."
        )
        if st.button("Valider et générer les 4 photos"):
            with st.spinner("Génération des 4 plans (≈ 15 s)…"):
                results = generate_listing_photos(
                    st.session_state.photos, st.session_state.draft
                )
            st.session_state.generated_photos = results
            st.session_state.spent += sum(r.cost for r in results)

    if st.session_state.generated_photos:
        render_gallery()
```

- [ ] **Step 3: Ajouter `render_gallery` avant le bloc « Style et photos »** (après `_load_decor_index`)

```python
def render_gallery() -> None:
    results = st.session_state.generated_photos
    st.caption(f"Coût cumulé de la fiche : {st.session_state.spent:.3f} $")
    columns = st.columns(2)
    for index, result in enumerate(results):
        with columns[index % 2]:
            st.markdown(f"**{result.label}**")
            if result.image is not None:
                st.image(result.image)
            if result.error:
                st.error(result.error)
            if result.verdict is not None and not result.verdict.ok:
                st.warning("Dérive possible : " + " ; ".join(result.verdict.problemes))
            st.checkbox("Garder", value=result.image is not None, key=f"keep_{result.shot_id}")
            feedback = st.text_input("Consigne (optionnel)", key=f"feedback_{result.shot_id}")
            if st.button("Régénérer ce plan", key=f"regen_{result.shot_id}"):
                with st.spinner("Régénération…"):
                    new_result = generate_shot(
                        st.session_state.photos,
                        st.session_state.draft,
                        SHOTS_BY_ID[result.shot_id],
                        feedback=feedback or None,
                    )
                st.session_state.spent += new_result.cost
                st.session_state.generated_photos[index] = new_result
                st.rerun()
```

- [ ] **Step 4: Vérifier que l'app se charge**

Run: `python3 -c "import ast,sys; ast.parse(open('app.py').read())" && pytest tests/ -q`
Expected: pas d'erreur de syntaxe, tous les tests passent.

Puis vérification manuelle :

```bash
streamlit run app.py
```

Déposer les 3 photos du t-shirt Peggy Sue's → Analyser → choisir le style (genre Femme, type Haut) → « Valider et générer les 4 photos ». Vérifier : 4 images en galerie, coût affiché, « Régénérer ce plan » avec une consigne remplace uniquement ce plan, un plan en erreur affiche le message sans casser les autres.

- [ ] **Step 5: Documentation**

Dans `AGENTS.md`, remplacer la ligne du seam PoC-2 par :

```
- `generate_listing_photos(photos, draft) -> list[ShotResult]` — frontière du PoC-2 V2 (4 plans, modèle image natif via OpenRouter + check de fidélité). Injecter `image_generator` / `fidelity_checker` dans les tests, jamais la logique de `shots.py`.
```

Dans le bloc `.env`, supprimer la ligne `FAL_KEY=...` et ajouter :

```
# PoC-2 V2 : modèle image, optionnel (défaut google/gemini-3.1-flash-image)
OPENROUTER_IMAGE_MODEL=google/gemini-3.1-flash-image
```

Dans `specs/2026-09-24-poc2-v2-generation-native-design.md`, remplacer la phrase « Cas limite : pas de `mannequin_ref` pour le genre → plan porté remplacé par un plan à plat, comme aujourd'hui. » par :

```
Cas limite : pas de `mannequin_ref` pour le genre → le plan porté est quand même généré, sans référence mannequin (personne générée librement). Remplacer le plan par un second à plat aurait dupliqué un plan existant.
```

- [ ] **Step 6: Commit**

```bash
git add app.py AGENTS.md specs/2026-09-24-poc2-v2-generation-native-design.md
git commit -m "poc-annonces: galerie 4 plans, régénération par plan, coût affiché; docs V2" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Test d'acceptation manuel

**Files:** aucun changement de code.

- [ ] **Step 1: Lancer la génération réelle avec les vrais modules**

Depuis `poc-annonces/`, avec `.env` chargé (t-shirt Peggy Sue's, sans decor_refs/mannequin, car ceux-ci exigent Drive) :

```bash
python3 - <<'EOF'
import glob, os
from dotenv import load_dotenv
load_dotenv()
from listing import ListingDraft
from photo_generation import generate_listing_photos

photos = [open(p, "rb").read() for p in sorted(glob.glob("Test_humain/Poc /Input/*.png"))]
draft = ListingDraft(titre="T-shirt Banned Retro", description="", mood="rétro pinup diner")
results = generate_listing_photos(photos, draft)
os.makedirs("Test_humain/V2", exist_ok=True)
for r in results:
    print(r.shot_id, "attempts", r.attempts, "cost", round(r.cost, 4),
          "verdict", None if r.verdict is None else (r.verdict.ok, r.verdict.problemes), "err", r.error)
    if r.image: r.image.save(f"Test_humain/V2/{r.shot_id}.png")
print("total", round(sum(r.cost for r in results), 3), "$")
EOF
```

Expected : 4 fichiers dans `Test_humain/V2/`, coût total ≈ 0,28-0,35 $, aucune erreur.

- [ ] **Step 2: Jugement humain**

Comparer `Test_humain/V2/` à `Test_humain/Gemini/Output/`. Critère de la spec : « meilleur que Gemini app ». Noter : fidélité de l'imprimé et du liseré, cohérence entre plans, verdicts du check (vrais positifs / faux positifs).

- [ ] **Step 3: Test avec la bibliothèque (Drive)**

Via `streamlit run app.py` (Task 5, Step 4) pour valider l'effet des `decor_refs` et du mannequin sur la cohérence entre plans. Si les 4 plans restent visuellement incohérents (pièces différentes), ouvrir la décision « repli collage 2×2 » prévue au spec.

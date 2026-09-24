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

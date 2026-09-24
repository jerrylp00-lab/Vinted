"""Utilitaires image partagés entre PoC-1 et PoC-2."""

from __future__ import annotations

import base64
import io

from PIL import Image

MAX_IMAGE_SIDE = 1280


def resize_to_data_url(photo: bytes, max_side: int = MAX_IMAGE_SIDE) -> str:
    image = Image.open(io.BytesIO(photo)).convert("RGB")

    width, height = image.size
    longest_side = max(width, height)
    if longest_side > max_side:
        scale = max_side / longest_side
        image = image.resize((round(width * scale), round(height * scale)))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"

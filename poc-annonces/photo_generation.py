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

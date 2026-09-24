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
            "The garment worn by a person of average build, framed as a mirror selfie; "
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

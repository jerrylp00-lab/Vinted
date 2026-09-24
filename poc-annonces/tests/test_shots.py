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

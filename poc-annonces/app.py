"""PoC-1 : interface Streamlit minimale pour générer une fiche Vinted.

Dépose des photos, obtiens un brouillon (titre/description/mood/questions),
puis affine par feedback en langage libre dans le même fil de chat.
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from listing import DEFAULT_MODEL, FALLBACK_MODELS, ListingError, generate_listing_draft

load_dotenv()

st.set_page_config(page_title="Fiches Vinted — PoC-1", page_icon="🧥")
st.title("🧥 Générateur de fiche Vinted (PoC-1)")

if "history" not in st.session_state:
    st.session_state.history = []
if "draft" not in st.session_state:
    st.session_state.draft = None
if "photos" not in st.session_state:
    st.session_state.photos = None

with st.sidebar:
    st.subheader("Modèle")
    model_options = [DEFAULT_MODEL, *FALLBACK_MODELS]
    model = st.selectbox("Modèle OpenRouter", model_options, index=0)

    if st.button("Nouvelle fiche"):
        st.session_state.history = []
        st.session_state.draft = None
        st.session_state.photos = None
        st.rerun()

uploaded_files = st.file_uploader(
    "Photos du vêtement",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

if st.button("Analyser", disabled=not uploaded_files):
    photos = [f.getvalue() for f in uploaded_files]
    st.session_state.photos = photos
    st.session_state.history = []
    try:
        st.session_state.draft = generate_listing_draft(photos, model=model)
    except ListingError as exc:
        st.error(str(exc))
        st.session_state.draft = None


def render_draft() -> None:
    draft = st.session_state.draft
    st.subheader(draft.titre)
    st.write(draft.description)
    st.caption(f"Mood : {draft.mood}")
    if draft.questions:
        with st.container(border=True):
            st.markdown("**Questions du modèle :**")
            for question in draft.questions:
                st.markdown(f"- {question}")


if st.session_state.draft is not None:
    render_draft()

    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    feedback = st.chat_input("Feedback ou réponse aux questions...")
    if feedback:
        st.session_state.history.append({"role": "user", "content": feedback})
        try:
            st.session_state.draft = generate_listing_draft(
                st.session_state.photos,
                history=tuple(st.session_state.history),
                model=model,
            )
            st.session_state.history.append(
                {"role": "assistant", "content": "Fiche mise à jour."}
            )
        except ListingError as exc:
            st.error(str(exc))
        st.rerun()

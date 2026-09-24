"""Interface Streamlit pour générer une fiche Vinted (PoC-1) et,
optionnellement, des photos stylées à partir de la bibliothèque Drive (PoC-2).

Dépose des photos, obtiens un brouillon (titre/description/mood/questions),
affine par feedback en langage libre, puis choisis un style et génère des
photos de sortie.
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from decor_selection import DecorSelectionError, select_decor_refs
from drive_client import build_drive_service
from library import LibraryError, load_index
from listing import DEFAULT_MODEL, FALLBACK_MODELS, ListingError, generate_listing_draft
from photo_generation import PhotoGenerationError, generate_listing_photos

load_dotenv()

GENRES = ["Femme", "Homme"]
TYPES_VETEMENT = ["Chaussures", "Haut", "Jupe", "Pantalon", "Robe", "Sac", "Veste", "Autre"]

st.set_page_config(page_title="Fiches Vinted", page_icon="🧥")
st.title("🧥 Générateur de fiche Vinted")

if "history" not in st.session_state:
    st.session_state.history = []
if "draft" not in st.session_state:
    st.session_state.draft = None
if "photos" not in st.session_state:
    st.session_state.photos = None
if "generated_photos" not in st.session_state:
    st.session_state.generated_photos = None

with st.sidebar:
    st.subheader("Modèle")
    model_options = [DEFAULT_MODEL, *FALLBACK_MODELS]
    model = st.selectbox("Modèle OpenRouter", model_options, index=0)

    if st.button("Nouvelle fiche"):
        st.session_state.history = []
        st.session_state.draft = None
        st.session_state.photos = None
        st.session_state.generated_photos = None
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
    st.session_state.generated_photos = None
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


@st.cache_resource
def _load_decor_index():
    return load_index()


if st.session_state.draft is not None and not st.session_state.draft.questions:
    st.divider()
    st.subheader("Style et photos (PoC-2)")

    col1, col2 = st.columns(2)
    genre = col1.selectbox("Genre", GENRES)
    type_vetement = col2.selectbox("Type de vêtement", TYPES_VETEMENT)

    if st.button("Choisir le style depuis la bibliothèque"):
        try:
            index_entries = _load_decor_index()
            service = build_drive_service()
            st.session_state.draft = select_decor_refs(
                genre, type_vetement, st.session_state.draft, index_entries, service
            )
        except (FileNotFoundError, KeyError, LibraryError, DecorSelectionError) as exc:
            st.error(f"Sélection du style impossible : {exc}")

    if st.session_state.draft.decor_refs:
        st.write(f"Références choisies : {', '.join(st.session_state.draft.decor_ref_labels)}")
        st.caption(f"Mood affiné : {st.session_state.draft.mood}")

        count = st.number_input("Nombre de photos à générer", min_value=1, max_value=6, value=3)
        porte_ratio = st.slider("Proportion \"porté\"", 0.0, 1.0, 0.5)

        st.info(
            "La génération d'image appelle Fal.ai et a un coût réel "
            "(~0,10-0,15 $/photo). Valide seulement quand tu es prêt."
        )
        if st.button("Valider et générer les photos"):
            try:
                st.session_state.generated_photos = generate_listing_photos(
                    st.session_state.photos,
                    st.session_state.draft,
                    count=int(count),
                    porte_ratio=porte_ratio,
                )
            except PhotoGenerationError as exc:
                st.error(str(exc))

    if st.session_state.generated_photos:
        st.image(st.session_state.generated_photos)

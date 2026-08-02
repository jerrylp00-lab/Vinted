import streamlit as st
import bot

st.title("Vinted bot — test")

query = st.text_input("Mot-clé", "Chaussure")

col1, col2 = st.columns(2)
min_likes = col1.number_input("Nombre de likes minimum", value=50, step=1)
max_age_hours = col2.number_input("Publié depuis (heures)", value=12.0, step=1.0)

exclude_promoted = st.checkbox("Exclure les annonces sponsorisées", value=True)

if st.button("Lancer"):
    with st.spinner("Recherche en cours..."):
        results = bot.find_trending(
            query,
            min_likes=int(min_likes),
            max_age_hours=max_age_hours,
            exclude_promoted=exclude_promoted,
        )

    st.write(f"{len(results)} résultat(s)")

    for r in results:
        with st.container(border=True):
            col_photo, col_info = st.columns([1, 3])
            with col_photo:
                if r.get("photo_url"):
                    st.image(r["photo_url"])
            with col_info:
                st.markdown(f"**{r['title']}** — {r['price']}")
                st.write(f"👍 {r['favourite_count']} likes · 👁 {r['view_count']} vues")
                st.write(f"Publié le {r['published_at']} ({r['age_hours']} h)")
                st.link_button("Voir l'annonce", r["url"])

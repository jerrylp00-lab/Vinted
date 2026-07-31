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
    st.dataframe([
        {
            "Titre": r["title"],
            "Prix": r["price"],
            "URL": r["url"],
            "Likes": r["favourite_count"],
            "Vues": r["view_count"],
            "Date de publication": r["published_at"],
            "Heures depuis publication": r["age_hours"],
        }
        for r in results
    ])

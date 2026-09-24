# poc-annonces

Proof-of-concept : automatisation de la génération de fiches Vinted (photos → texte + photos stylées). Lire `CONTEXT.md` avant toute modification ici — il fixe le vocabulaire du domaine.

## Specs

Les specs de cette feature vivent dans `specs/`. Lire la spec concernée avant d'implémenter.

## Seams

- `generate_listing_draft(photos) -> ListingDraft` — frontière du PoC-1 (appel OpenRouter vision+JSON). Mocker la réponse HTTP dans les tests, pas le prompt interne.
- `generate_listing_photos(photos, draft) -> list[ShotResult]` — frontière du PoC-2 V2 (4 plans, modèle image natif Nano Banana 2 via Fal.ai + check de fidélité). Injecter `image_generator` / `fidelity_checker` dans les tests, jamais la logique de `shots.py`.

## Contexte voisin

L'ancien projet Vinted (détecteur de tendances, notifications WhatsApp) est archivé dans `../Archive/` — feature indépendante, sans lien avec `poc-annonces`, possible réactivation future.

## Lancer

Depuis `poc-annonces/` :

```bash
pip install -r requirements.txt
```

Créer un fichier `.env` (jamais commité, voir `.gitignore` à la racine) avec :

```
OPENROUTER_API_KEY=sk-or-...
# optionnel, sinon google/gemini-2.5-flash-lite par défaut
OPENROUTER_MODEL=google/gemini-2.5-flash-lite

# PoC-2 uniquement — GOOGLE_SERVICE_ACCOUNT_FILE (chemin, pratique en
# local) ou GOOGLE_SERVICE_ACCOUNT_JSON (contenu JSON inline, pratique
# avec le secret manager d'une plateforme de déploiement type Streamlit
# Community Cloud — jamais les deux, GOOGLE_SERVICE_ACCOUNT_JSON prime)
GOOGLE_SERVICE_ACCOUNT_FILE=/chemin/vers/service-account.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=<id du dossier "Modèles photos">
FAL_KEY=<clé api fal.ai>  # génération des photos (Nano Banana 2)
# optionnel, sinon fal-ai/nano-banana-2/edit par défaut
FAL_IMAGE_MODEL=fal-ai/nano-banana-2/edit
```

Ni le fichier JSON ni son contenu ne doivent jamais être commités sur
GitHub — en local via `.env` (gitignoré), en déploiement via le secret
manager de la plateforme (jamais dans le code ni dans le repo).

Lancer les tests (aucune clé API requise, tout est mocké) :

```bash
pytest tests/ -v
```

Lancer l'app :

```bash
streamlit run app.py
```

### PoC-2 : indexer la bibliothèque

Le dossier Drive "Modèles photos" doit être partagé (rôle Lecteur) avec
l'email du service account. Relancer à chaque ajout de nouvelles photos :

```bash
python index_library.py
```

Produit `decor_index.json` (non commité — spécifique à la bibliothèque de
chaque vendeur), lu par `app.py` au démarrage.

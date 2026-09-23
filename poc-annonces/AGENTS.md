# poc-annonces

Proof-of-concept : automatisation de la génération de fiches Vinted (photos → texte + photos stylées). Lire `CONTEXT.md` avant toute modification ici — il fixe le vocabulaire du domaine.

## Specs

Les specs de cette feature vivent dans `specs/`. Lire la spec concernée avant d'implémenter.

## Seams

- `generate_listing_draft(photos) -> ListingDraft` — frontière du PoC-1 (appel OpenRouter vision+JSON). Mocker la réponse HTTP dans les tests, pas le prompt interne.
- `generate_listing_photos(photos, draft) -> list[Image]` — frontière du PoC-2 (segmentation + inpainting + composite). Mocker les appels Fal.ai dans les tests.

## Contexte voisin

L'ancien projet Vinted (détecteur de tendances, notifications WhatsApp) est archivé dans `../Archive/` — feature indépendante, sans lien avec `poc-annonces`, possible réactivation future.

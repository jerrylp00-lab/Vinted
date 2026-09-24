# PoC-2 V2 — génération photo par modèle image natif

Statut : design validé le 2026-09-24, spike en cours. Remplace l'approche PoC-2 initiale (segmentation + inpainting + composite, Fal.ai).

## Pourquoi

Le test humain du 2026-09-24 (`Test_humain/`) a montré que le pipeline segmentation + inpainting + composite ne peut pas produire les photos voulues (pas de vêtement porté, pas de re-pose, fond noir, aucune cohérence) et que son prompt (`"Décor {mood}, {style}"`) ne porte aucune direction artistique. Gemini (app), avec un brief complet et 3 photos, produit un résultat nettement supérieur. Cause : mauvaise architecture, pas l'API.

## Décisions

| Sujet | Décision |
|---|---|
| Fidélité | Fidèle à l'œil + relecture humaine. Check vision auto en filet, jamais bloquant. |
| Bibliothèque Drive / `decor_index.json` | Conservée : 2-3 `decor_refs` envoyées comme images de référence de style. |
| Mannequin maison | Conservé, envoyé comme référence sur le plan « porté » uniquement. |
| Plans | 4 fixes : porté (selfie miroir), à plat, cintre, détail. |
| Appels | 4 appels séparés, un par plan (pleine résolution, régénération par plan). |
| Modèle | Nano Banana 2 (Gemini image) via Fal.ai, `fal-ai/nano-banana-2/edit`, 0,08 $/image en 1K, `FAL_KEY` (crédit déjà acheté). Spike OpenRouter aussi validé (`google/gemini-3.1-flash-image`, ~0,07 $), utilisé en repli automatique quand le crédit Fal est épuisé (`IMAGE_PROVIDER=auto`). |
| Entrées | Photos brutes de téléphone (pas de nettoyage de cadres). |
| Relecture | Galerie : garder / rejeter / régénérer un plan avec consigne libre. |
| Succès | Meilleur que l'app Gemini. Test d'acceptation manuel sur le t-shirt Peggy Sue's. Coût loggé et affiché, sans plafond. |

## Architecture

```
photos brutes ─► PoC-1 (texte, mood, decor_refs) ─► Validation du plan
        pour chacun des 4 plans :
        brief(plan, mood) + photos vêtement + decor_refs (+ mannequin si porté)
                  ─► modèle image (OpenRouter)
                  ─► check fidélité (LLM vision, original vs sortie)
                  ─► galerie (garder / rejeter / régénérer + consigne)
```

Modules :
- `shots.py` — les 4 plans en données : brief, refs requises, cadrage, règles. C'est le harnais.
- `image_gen.py` — appel Fal.ai, N images en entrée, 1 image en sortie, usage/coût remonté.
- `fidelity.py` — check vision, verdict `{ok, problemes[]}`.
- `photo_generation.py` — orchestration. Garde la frontière `generate_listing_photos(photos, draft)`.
- Supprimés : `FalClient`, `_mask_from_alpha`, `_composite` (Fal reste utilisé, mais via le modèle image natif).

## Harnais (brief)

Couche commune : direction artistique « effortless chic » parisien / UGC, rendu smartphone ou argentique 35mm, lumière naturelle, ombres douces, grain léger, aucun rendu 3D/CGI/studio blanc, tombé naturel. Ancrage de fidélité : reproduire exactement imprimé, texte, liseré, couleur et coupe des photos jointes, n'inventer aucun détail. Mood issu des `decor_refs`, envoyées comme inspiration d'ambiance (ne pas copier la pièce).

Couche par plan (contenu repris du prompt Gemini validé par l'utilisateur) :
1. Porté, selfie miroir : morphologie standard, visage entièrement caché par le smartphone, appartement parisien vintage, parquet, fenêtre. Reçoit le mannequin.
2. À plat : légèrement drapé, surface vintage texturée, lumière douce, ombres réalistes.
3. Cintre : cintre bois, mur blanc cassé à moulures, arrière-plan flou (portant, chaise vintage).
4. Détail : plan très rapproché, tenu par une main, focus texture/boutons/coutures, lumière directe.

Cas limite : pas de `mannequin_ref` pour le genre → le plan porté est quand même généré, sans référence mannequin (personne générée librement). Remplacer le plan par un second à plat aurait dupliqué un plan existant.

## Fidélité, erreurs, coût

- Le check renvoie les dérives ; 1 retry automatique, puis flag visible dans la galerie. Jamais de blocage.
- Aucune image renvoyée (filtre, quota) : erreur affichée pour ce plan, les autres continuent, relance possible seul.
- Coût réel (génération + check) loggé et affiché par fiche.

## Risque connu

Cohérence entre les 4 appels séparés (deux pièces différentes). Mitigation : mêmes refs et même brief de style. Repli si insuffisant : un appel produisant un collage 2×2, à découper.

## Tests

- Unitaires : construction des briefs par `shots`, `image_gen` (réponse OpenRouter mockée), orchestration avec un plan en échec.
- Acceptation manuelle : t-shirt Peggy Sue's, mêmes 3 photos, comparaison avec `Test_humain/Gemini`.
- Spike préalable : voir ci-dessous.

## Spike (avant tout code de production)

Question : Gemini image sur OpenRouter accepte-t-il plusieurs images en entrée et renvoie-t-il une image ? Quel coût et quelle latence ?
Sortie du spike : modèle retenu, forme exacte de la requête et de la réponse, coût/latence mesurés, et 4 images de test à juger contre la référence Gemini.

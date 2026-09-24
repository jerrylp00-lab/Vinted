# poc-annonces-n8n

Back-end n8n des fiches Vinted. Spec : `specs/2026-09-24-backend-n8n-design.md`.

Instance : `https://178-105-102-54.sslip.io` (projet personnel `TXEVSUXNA9B85FIU`).

## Étape 0 — état (2026-09-24)

Data Tables créées (colonnes de liste/objet stockées en JSON dans une colonne `string` ; l'`id` de ligne est automatique) :

| Table | ID |
|---|---|
| `library` | `szOLa2GMVs8D2AHi` |
| `users` (lignes `Jeremy`, `Associé` créées) | `yh8LhSW0DxPdDk4Y` |
| `jobs` | `vVa4oB747ymKwzw8` |
| `shots` | `qssjFRjdNaiMzoNG` |
| `feedback` | `kpIOnnr4JrfK2L1U` |
| `prompts` | `vqb7uMK180X3MbKm` |

Écarts avec la spec : les colonnes `created_at`/`updated_at` ne sont pas déclarées (n8n les gère nativement) ; `verdict_fidelite` de `shots` est éclaté en `fidelite_ok` + `fidelite_problemes` ; le `drive_folder_id` de la bibliothèque et l'ID du dossier `_inbox` sont à renseigner à l'étape 1.

Workflow de test : `VFN — Ping (étape 0)` (`WkIakEqtrwkjr9vs`), webhook `POST /webhook/vfn/ping`. CORS vérifié depuis `Origin: null` (preflight avec header `x-vfn-secret` accepté).

Secret : credential Header Auth `VFN webhook secret` (`dXkTZ5dYJAP4A5v9`, header `X-VFN-Secret`) activé sur le ping. Vérifié : sans secret ou avec un mauvais secret → 403.

**Étape 0 terminée.**

## Étape 1 — Indexation de la bibliothèque (2026-09-24)

Workflow `VFN — Indexation bibliothèque` (`k7j9FcAjqQKLYCj1`, publié) :
- Déclencheurs : manuel, et `POST /webhook/vfn/library/reindex` (secret requis).
- Parcourt le Drive (racine `1yvC8E9EZw3dux01jhvjZMIa_tjEfl8n-`, structure `genre/type/photo`, 3 requêtes Drive au total), ignore `Mannequin/*` et les photos déjà présentes dans `library` (relancer ne réindexe que les nouvelles ; max 100 par exécution).
- Réduit chaque photo à 1024 px, l'envoie à `google/gemini-2.5-flash-lite` (OpenRouter) avec le prompt actif `indexation_photo`, réponse JSON stricte (description, tags, 1 à 3 moods choisis dans la liste).
- Insère une ligne par photo dans `library` (`source = import_initial`).

Prompts créés dans la table `prompts` (v1, actifs) : `moods_liste` (10 moods, une ligne `id | définition`, modifiable) et `indexation_photo`.

Résultat : 23 photos indexées en 55 s, environ 0,0003 $ chacune. Une seconde exécution n'indexe rien (idempotent).

À faire plus tard pour l'étape 1 : trigger sur le dossier `_inbox` et endpoint d'upload (avec le front, étape 6), export JSON des workflows dans `workflows/`, pagination Drive au-delà de 1000 éléments par niveau.

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

## Étape 2 — Texte de la fiche (2026-09-24)

Workflows (tous publiés, webhooks protégés par `X-VFN-Secret`, CORS ouvert) :

| Workflow | ID | Rôle |
|---|---|---|
| `VFN — Créer une fiche (webhook)` | `5erMviLZ0qLPtd1E` | `POST /webhook/vfn/job` (multipart : `user`, `genre`, `type_vetement`, `moods_autorises` en JSON, photos `photo0`, `photo1`…). Répond tout de suite `{job_id}`, crée le dossier Drive `VFN Fiches/<date>_<job_id>/input/`, enregistre le job, envoie les photos, lance la génération. |
| `VFN — Générer le texte (sous-workflow)` | `gdGJLLnGtW79Jeol` | Relit les photos du dossier `input`, assemble le prompt actif `texte_fiche` + profil du user + historique, appelle `google/gemini-2.5-flash-lite`, met à jour le job (`texte_pret` ou `erreur`) et le coût. |
| `VFN — Affiner le texte (webhook)` | `bRdAbgJiiGKwNyvP` | `POST /webhook/vfn/job/texte` `{job_id, message}` : ajoute la réponse ou le feedback à l'historique et régénère. |
| `VFN — Lire une fiche (statut)` | `3EkEko4Qo2ofd7LK` | `GET /webhook/vfn/job-status?id=<job_id>` (polling du front). 404 si inconnu. |

Écart avec la spec : le statut est `GET /job-status?id=` et non `GET /job/:id` (un chemin dynamique préfixerait l'URL d'un identifiant de webhook).

Ajouts à `jobs` : `genre`, `type_vetement`, `drive_input_folder_id`, `questions` (JSON), `historique` (JSON, messages `user`/`assistant`). Prompt `texte_fiche` v1 dans `prompts` (`{profil}` remplacé par `users.preferences_md`). Dossier Drive racine des journaux : `VFN Fiches` (`1BupqpOHcBFnoILebfox-GjVTlm_gz-AB`, hors de la bibliothèque pour ne pas être indexé).

Test réalisé : sur un job de test (`test1`, photos de la bibliothèque), génération en 8 s pour 0,0002 $, puis affinage avec un message utilisateur (la marque et la taille ont été intégrées). Le webhook de création (upload multipart) n'a pas encore été appelé pour de vrai : `scripts/test_job.sh` le fait (`VFN_SECRET=... ./scripts/test_job.sh femme jupe photo1.jpg …`).

Reste : la ligne de job `test1` est un reste de test dans la table `jobs` (à supprimer depuis l'UI n8n) ; `decor_refs` est vide jusqu'à l'étape 3.

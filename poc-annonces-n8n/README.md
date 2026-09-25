# poc-annonces-n8n

> **V3** : 3 photos par fiche (`porte_miroir`, `cintre`, `detail`) sans check ni retry automatique, mood et inspirations choisis par l'humain (2 en vision, 3 en texte anglais), mannequin et vêtement décrits en texte. Coût mesuré : 0,24 $ par fiche (0,40 $ avant, à nombre d'images comparable). Détails : étape 9 ci-dessous.

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

Tests réalisés : (1) sous-workflow sur un job de test (`test1`) : 8 s, 0,0002 $, puis affinage avec un message utilisateur (marque et taille intégrées) ; (2) de bout en bout via `scripts/test_job.sh` avec 3 vraies photos (`VFN_SECRET=... ./scripts/test_job.sh femme haut photo1.png …`) : job créé, photos envoyées sur Drive, texte prêt en ~15 s pour 0,0002 $. La réponse `{job_id}` du webhook de création n'est renvoyée qu'après l'écriture du job, sinon le premier poll du statut tombait sur un 404.

Reste : les lignes de test de la table `jobs` (`test1` et deux jobs de `test_job.sh`) sont à supprimer depuis l'UI n8n ; `decor_refs` est vide jusqu'à l'étape 3.

## Étape 3 — Sélection du style et validation (2026-09-24)

> Remplacé à l'étape 9 : la sélection du style n'appelle plus de LLM (pool filtré et trié par `utilisations`, choix final humain), le mannequin n'est plus une image mais une description texte (`config_mannequins` v2 : genre → description ; v1 genre → id Drive, inactif). Voir « Étape 9 ».

| Workflow | ID | Rôle |
|---|---|---|
| `VFN — Sélectionner le style (sous-workflow)` | `FI9HyhPdvbATuSqw` | Filtre `library` (actif, même genre et type, moods autorisés ; à défaut même genre et moods avec avertissement ; sinon aucune référence), tire jusqu'à 10 candidates, jugement visuel du LLM (`selection_style`) qui en garde 2 à 3 et dérive le mood, associe le mannequin du genre (`config_mannequins`). Statut → `en_attente_validation`. |
| `VFN — Choisir le style (webhook)` | `ao81dPakf9IqTIyr` | `POST /webhook/vfn/job/style` `{job_id, moods_autorises?: [...]}` : lance ou relance la sélection (statuts acceptés : `texte_pret`, `en_attente_validation`, `erreur`). Sert aussi de « retirer au sort ». |
| `VFN — Valider le plan (webhook)` | `z1SY3ZkptHVSd4al` | `POST /webhook/vfn/job/valider` `{job_id, mood?, decor_refs?: [file_id, ...]}` : applique les corrections (les ids doivent exister et être actifs dans `library`), statut → `generation_en_cours`. 409 si le job n'est pas `en_attente_validation`. **Ne déclenche pas encore la génération (étape 4).** |

Nouveaux champs de `jobs` : `avertissements` (JSON, ex. « pas de mannequin pour ce genre »), `mannequin_file_id`. `decor_refs` est une liste JSON d'objets `{file_id, nom_fichier, type_vetement, moods, tags}`. Nouveaux prompts : `selection_style` v1 et `config_mannequins` v1 (JSON genre → id de fichier Drive du mannequin, modifiable dans la table). Le statut (`GET /job-status`) renvoie maintenant aussi `mannequin_file_id` et `avertissements`.

Tests (en production, avec le secret) : sélection sur un job `femme/veste` restreint aux moods `urbain_minimaliste` et `streetwear_decontracte` → 2 références cohérentes en ~10 s pour 0,0001 $ ; validation avec mood et référence corrigés → statut `generation_en_cours`, corrections appliquées ; seconde validation → 409.

Le front devra afficher les images de `decor_refs` : il faudra un endpoint d'aperçu des photos Drive (étape 6), les fichiers n'étant pas publics.

## Étape 4 — Génération des 4 plans (2026-09-24)

> Remplacé à l'étape 9 : 3 plans (`porte_miroir`, `cintre`, `detail`), plus de plan `a_plat`, une seule tentative par plan (plus de retry automatique), plus de check de fidélité, plus d'image de mannequin envoyée. Voir « Étape 9 ».

| Workflow | ID | Rôle |
|---|---|---|
| `VFN — Tentative image (sous-workflow)` | `pGvWMH08Go4yGJYp` | Une tentative pour un plan : test du plafond de coût, assemblage du brief (prompts `brief_*`) et des références (photos du vêtement, decor_refs, mannequin sur le plan porté), appel Fal (Nano Banana 2) avec repli OpenRouter sur 402/403, check de fidélité (LLM vision), envoi sur Drive `output/`, ligne `shots`. Une panne du check ne perd pas l'image (`fidelite_verifiee = false`). |
| `VFN — Générer un plan (sous-workflow)` | `HKMVyeJJQTSoBN6X` | Tentative 1, et 1 retry automatique avec les problèmes relevés si le vêtement dérive ; puis passe le job à `galerie_prete` (ou `budget_depasse`) quand les 4 plans ont une tentative courante. |
| `VFN — Générer les 4 plans (sous-workflow)` | `9Y0O9Z4MO9wVM0xB` | Crée le dossier Drive `output/`, statut `generation_en_cours`, lance les 4 plans **en parallèle** (sans attendre). |
| `VFN — Régénérer un plan (webhook)` | `MIeRXvNz9a4cwKIo` | `POST /webhook/vfn/job/plan` `{job_id, plan, feedback?, force?}` : refuse (409) si la galerie n'est pas prête ou si le plan est inconnu ; consigne un feedback négatif implicite dans `feedback` ; relance le plan. `force: true` outrepasse le plafond de coût. |

Modifiés : `Valider le plan` lance maintenant la génération ; `GET /job-status` renvoie `plans[]` (état du plan courant : `en_attente` / `pret` / `erreur`, tentative, `drive_file_id`, fidélité, problèmes, coût du plan, fournisseur, `garde`) et les coûts `cout_texte`, `cout_images`, `cout_total`.

Nouveaux champs : `jobs.drive_output_folder_id` ; `shots.erreur`, `courant`, `brief` (prompt exact envoyé), `fidelite_verifiee`. Nouveaux prompts (v1) : `brief_commun`, `brief_ref_vetement`, `brief_ref_decor`, `brief_ref_mannequin`, `brief_plan_{porte_miroir,a_plat,cintre,detail}`, `check_fidelite`, `config_plafond` (`plafond_usd` 1,0 ; `estimation_tentative_usd` 0,1) et `config_image` (modèles Fal et OpenRouter, format, résolution, coût par unité Fal).

Test réel (job `mufe74xl35gs`, t-shirt Peggy Sue's Diner, 2 références) : validation → 4 plans en environ 1 minute, tous sur Fal. Le plan `porte_miroir` a dérivé (texte du t-shirt modifié), a été retenté une fois, reste signalé avec ses problèmes ; les 3 autres sont conformes. Coût des images : 0,40 $ (le contrôle de fidélité coûte des millièmes de dollar). Régénération du plan `detail` avec consigne : 2 tentatives (la première dérivait), statut revenu à `galerie_prete`, total 0,56 $. Le repli OpenRouter n'a pas été exercé (Fal a du crédit) et le plafond de 1 $ n'a pas été atteint en test.

Limites connues : si une étape plante hors des cas prévus (ex. Drive indisponible), le plan n'écrit pas de ligne et le job reste en `generation_en_cours` (pas de reprise automatique ; un workflow d'erreur global reste à prévoir). Le « garder » d'un plan (colonne `garde`) et les pouces arrivent avec l'étape 5. Le brief de chaque tentative est conservé dans `shots.brief` ; le `log.json` Drive est à faire à l'étape 5.

## Étape 5 — Feedback et journal Drive (2026-09-24)

> Remplacé à l'étape 9 : les cibles de feedback par plan sont `porte_miroir`, `cintre`, `detail` ; le journal ne contient plus de données de fidélité vérifiée (`fidelite_verifiee = false`). Voir « Étape 9 ».

| Workflow | ID | Rôle |
|---|---|---|
| `VFN — Feedback (webhook)` | `DgoKnyLMpuLqabFh` | `POST /webhook/vfn/job/feedback` `{job_id, cible, note, raisons?, commentaire?}`. `cible` : `description`, `plan:<porte_miroir\|a_plat\|cintre\|detail>` ou `global` (note finale). `note` : `up` / `down` (stockée 👍 / 👎). Un nouvel avis sur la même cible **remplace** le précédent (les régénérations, signal implicite, restent en lignes séparées). Les `raisons` doivent appartenir au vocabulaire de la cible (ligne `config_feedback` de `prompts`, modifiable) sinon 400 avec la liste autorisée ; 404 si le job n'existe pas ; 409 pour un avis sur un plan avant que la galerie soit prête. La note `global` passe le job à `termine` et écrit le journal. |
| `VFN — Garder un plan (webhook)` | `TrqnPOfRw7NLEEzz` | `POST /webhook/vfn/job/garder` `{job_id, plan, garde: true/false}` : coche ou décoche « Garder » sur le plan courant. |
| `VFN — Écrire le journal Drive (sous-workflow)` | `LtGZGU42Lkx2ip3u` | Écrit `log.json` dans le dossier Drive du job (créé la première fois, puis mis à jour ; son id est dans `jobs.drive_log_file_id`) : entrées, texte et historique de l'échange, références et mannequin, versions de prompt, toutes les tentatives d'image avec leur brief exact, verdicts, feedback, coûts. Appelé quand la galerie est prête et à la note finale. |

`GET /job-status` renvoie aussi `feedback` (dernier avis explicite par cible, avec raisons et commentaire). Vocabulaire initial des raisons de 👎 : description (`faits_faux`, `ton_inadapte`, `trop_court`, `trop_long`, `info_manquante`, `autre`), plan (`couleur_fausse`, `vetement_deforme`, `texte_ou_imprime_modifie`, `ambiance_ratee`, `rendu_irrealiste`, `autre`), global (`qualite_photos`, `qualite_texte`, `ambiance_ratee`, `trop_cher`, `autre`).

Test réel sur `mufe74xl35gs` : 👍 description, puis changement d'avis en 👎 « trop court » (remplacé, pas dupliqué) ; 👎 sur `porte_miroir` avec raison et commentaire ; raison inconnue → 400 ; job inconnu → 404 ; « garder » décoché sur `porte_miroir` ; note finale 👍 avec commentaire → statut `termine` ; `log.json` créé dans le dossier du job (17 Ko).

Limite : si les 4 plans finissent au même instant, deux `log.json` pourraient être créés la première fois (risque faible, sans conséquence sur les données).

## Étape 6 — Front HTML et endpoints associés (2026-09-24)

> Remplacé à l'étape 9 : le front décrit ici (4 plans, avertissement de fidélité, mannequin) a été refait : formulaire, choix humain des inspirations, écran de relecture, galerie à 3 plans. Voir « Étape 9 ».

Front : `front/index.html`, un seul fichier sans dépendance. Il se lance en local (`cd poc-annonces-n8n/front && python3 -m http.server 8765`, puis http://127.0.0.1:8765) ou en l'ouvrant directement. Au premier lancement, la fenêtre **Réglages** demande l'URL des webhooks (par défaut `https://178-105-102-54.sslip.io/webhook/vfn`) et le secret ; ils sont gardés dans le `localStorage` du navigateur, jamais dans le fichier. Sélecteur d'utilisateur en haut (liste lue dans la table `users`).

- **Nouvelle fiche** : photos, genre, type (suggestions issues de la bibliothèque), moods autorisés (cases à cocher) → texte (avec questions du modèle, feedback en langage libre, 👍/👎 avec raisons, copie du titre et de la description) → choix du style (références avec case pour les retirer, mood éditable, avertissements, « retirer au sort ») → validation, qui ouvre la galerie.
- **Galerie** : ouverture d'une fiche par identifiant ; les 4 plans avec avertissement de fidélité, coût par plan et total, « Garder », téléchargement, 👍/👎 avec raisons, régénération avec consigne (case « dépasser le plafond » si nécessaire), note finale avec commentaire. Rafraîchissement automatique pendant les étapes longues.
- **Bibliothèque** : grille filtrable (genre, type, mood, actives), moods modifiables d'un clic (3 maximum par photo), activer/désactiver, ajout de photos (genre + type, dossier Drive créé si besoin, indexation LLM lancée automatiquement).

Les images Drive étant privées, le front les récupère avec l'en-tête secret et les affiche depuis des URL locales (chargement différé, 3 requêtes en parallèle).

Nouveaux workflows (webhooks protégés par secret) :

| Workflow | ID | Endpoint |
|---|---|---|
| `VFN — Configuration pour le front` | `fES1vA8Ak6Vz9N6K` | `GET /config` : moods (avec définitions), users, genres, types connus par genre, plans, vocabulaire des raisons, plafond |
| `VFN — Lire la bibliothèque` | `g1m9isMxo3gWGuV3` | `GET /library` |
| `VFN — Modifier une photo de la bibliothèque` | `kNGZI3ZZSRlckkgP` | `POST /library/update` `{drive_file_id, moods?, tags?, actif?}` (moods validés contre la liste fermée, 3 maximum) |
| `VFN — Ajouter des inspirations` | `a6h3K0SfbhFY4cBp` | `POST /library/upload` multipart (`genre`, `type_vetement`, `photo0`…) puis indexation |
| `VFN — Aperçu d'une image Drive` | `XKXHym7UwzHoh6in` | `GET /image?id=` : image réduite (jpeg 1000 px) ; refuse (404) tout identifiant qui n'est ni dans la bibliothèque, ni dans les plans générés, ni un mannequin configuré |

L'indexation (`k7j9FcAjqQKLYCj1`) a un troisième déclencheur (appel depuis un autre workflow) pour le dépôt de photos.

Testé : endpoints en `curl` ; front dans le navigateur intégré sur une fiche réelle (galerie avec les 4 images, états 👍/👎/garder relus depuis le serveur, bibliothèque de 23 photos avec chargement différé) ; création d'une nouvelle fiche par le formulaire puis choix du style. Non testés dans l'interface : la validation finale depuis le formulaire (~0,35 $), l'upload de nouvelles inspirations, le repli sur un secret erroné.

Limite : le fichier `front/index.html` n'a pas de style final ; c'est le fond fonctionnel, à habiller dans la phase design.

## Étape 7 — Ajustement des prompts (2026-09-24)

> Remplacé à l'étape 9 : il n'y a plus de dérive de fidélité (le check est supprimé), donc ce signal est toujours vide ; `meta_ajustement` v1 décrit encore 4 photos et un check de fidélité. Voir « Étape 9 », limites connues.

Boucle voulue : **propose → tu lis le diff → tu actives ou pas → retour arrière possible**. Aucun prompt n'est jamais modifié automatiquement.

| Workflow | ID | Endpoint |
|---|---|---|
| `VFN — Proposer un ajustement de prompt` | `5K6sfWDDQVc8NpI4` | `POST /prompts/propose` `{nom, jours?}` |
| `VFN — Lister les prompts` | `nqG841Bhc9LJWE66` | `GET /prompts` (toutes les versions, actif, notes, texte, `ajustable`) |
| `VFN — Activer une version de prompt` | `GBUtNGync3iN147g` | `POST /prompts/activer` `{nom, version}` (désactive les autres versions du même prompt ; sert aussi au retour arrière) |

Fonctionnement de la proposition : le workflow lit les retours de la période (30 jours par défaut, `config_ajustement`) qui concernent le prompt choisi et construit un dossier de preuves : pouces et raisons, commentaires, régénérations (signal implicite), et selon le prompt les corrections du texte que l'utilisateur a demandées (`texte_fiche`) ou les dérives de fidélité détectées sur les tentatives (prompts d'image). Chaque `brief_plan_*` ne regarde que son plan ; `brief_commun` et `brief_ref_*` regardent les 4. Sans signal négatif suffisant (`min_signaux`), il répond « pas assez de signaux » sans appeler le LLM. Sinon `anthropic/claude-sonnet-5` (modifiable dans `config_ajustement`) reçoit le prompt actuel, le dossier et les consignes de `meta_ajustement`, et renvoie le nouveau texte complet, la liste des changements justifiés, ses hypothèses et un niveau de confiance. Garde-fou : la proposition est **rejetée** si un jeton `{...}` du prompt d'origine disparaît ou si un nouveau apparaît. Elle est enregistrée dans `prompts` avec `actif = false`, version suivante, et `notes` (date, nombre de signaux, confiance, résumé) ; la réponse contient le diff. Les prompts `config_*`, `moods_liste` et `meta_ajustement` ne sont pas ajustables automatiquement.

Front : nouvel onglet **Prompts** (choix du prompt, « Proposer un ajustement », liste des versions avec notes, texte, différences avec la version active, « Activer cette version »).

Pas de notification Telegram (abandonnée) : on consulte les propositions dans l'onglet Prompts. Le champ `chat_id` de `config_ajustement` est un reste inutilisé.

Test réel : sur `brief_plan_porte_miroir`, 3 signaux (1 👎 avec le commentaire « le texte du t-shirt est faux », 2 dérives de fidélité) → proposition v2, confiance **faible** (à raison : très peu de données), pour 0,010 $ : une seule phrase ajoutée au brief (« reproduire exactement le texte, logo ou illustration imprimés, avec le bon sens de lecture »). Liste, refus (`config_image` → 400), activation de la v2, retour arrière sur la v1 et version inconnue (404) testés. **La v2 est laissée inactive** ; la v1 est bien la version active.

Limites : la version d'un prompt d'image utilisée par une fiche n'est pas stockée dans le job (seul le brief exact l'est dans `shots.brief`) : le dossier de preuves ne filtre donc pas par version, et après une activation il faut laisser passer quelques fiches avant de re-proposer. Le workflow n'évalue pas si une version activée a réellement amélioré les résultats : c'est à toi de comparer les retours avant/après.

## Ménage n8n (2026-09-24)

Archivés dans n8n (restaurables depuis l'interface) : `Test Drive — bibliothèque`, `Test Fal — image` et `VFN — Ping (étape 0)` (les webhooks de ping et de test ne servent plus, le front vérifie le secret en appelant `/config`). Le nœud Telegram du workflow d'ajustement a été retiré.

## Étape 8 — Profil user et exemples (2026-09-24)

Deux apports à la rédaction du texte, avec un coût de tokens borné et **uniquement à l'étape texte** (jamais dans les prompts image) :

- **Profil de préférences** par utilisateur (`users.preferences_md`), plafonné à 1500 caractères (≈ 300 tokens, `config_profil.max_chars`), injecté à la place du jeton `{profil}` du prompt `texte_fiche`.
- **Exemples** (few-shot en texte seul) : jusqu'à 2 annonces que tu as déjà notées 👍 sur la description (même genre et type en priorité, à défaut même genre ; les plus récentes ; 1200 caractères chacune), injectées à la place du jeton `{exemples}`. Aucun exemple = section omise. Les identifiants des exemples utilisés sont conservés dans `jobs.prompt_versions.exemples` (donc dans `log.json`).

Le prompt `texte_fiche` est passé en **v2** (ajout du jeton `{exemples}`) et activée ; la v1 reste disponible dans l'onglet Prompts pour revenir en arrière (sans jeton, les exemples sont alors simplement ignorés).

| Workflow | ID | Endpoint |
|---|---|---|
| `VFN — Lire le profil user` | `CgSPgAdmyCA356HI` | `GET /users/profil?user=` → `{user, preferences_md, max_chars}` |
| `VFN — Enregistrer le profil user` | `AT3l77KOj11xSIuV` | `POST /users/profil` `{user, preferences_md}` (400 au-delà de la limite) |
| `VFN — Proposer une mise à jour du profil user` | `PHlT76TnZbViAFlw` | `POST /users/profil/propose` `{user, jours?}` : dossier de preuves (corrections de texte demandées, avis sur les descriptions, notes finales des 60 derniers jours) → proposition de profil, **jamais appliquée** ; prompt `meta_profil`, modèle de `config_ajustement` |

Front : nouvel onglet **Profil** (édition avec compteur, « Proposer une mise à jour depuis mes retours », « Utiliser cette proposition » puis « Enregistrer »).

Corrigé au passage : le modèle de texte renvoie parfois un JSON avec un saut de ligne brut dans une chaîne (fiche en erreur « Unterminated string ») ; le parsing tente maintenant une réparation avant d'échouer.

Tests réels : profil de test enregistré (« éviter les superlatifs », « terminer par une phrase sur l'état général ») + 👍 sur la description d'une fiche femme/haut → nouvelle fiche femme/haut : le prompt envoyé contenait bien le profil et l'exemple (un seul approuvé pour l'instant), la description a respecté le profil (aucun superlatif, phrase finale sur l'état) ; +0,0002 $ de tokens par fiche. La proposition de profil sur les données de test a été prudente (confiance faible, peu de retours répétés) ; profil de test remis à vide, rien n'est appliqué tant que tu ne l'enregistres pas.

Limites : les exemples ne sont pas filtrés par utilisateur (toutes les annonces 👍 du même genre/type servent, y compris celles de l'associé) ; la sélection des exemples lit toute la table `jobs` et `feedback`, ce qui restera rapide pour quelques centaines de fiches.

## Sauvegarde et emplacement Drive (2026-09-24)

- **Tout est dans le dossier partagé `Modèles photos`** (id `1yvC8E9EZw3dux01jhvjZMIa_tjEfl8n-`, propriétaire : le compte Google connecté à n8n) : `VFN Fiches/` (un dossier par fiche : `input/`, `output/`, `log.json`) et `VFN Sauvegardes/` (un dossier daté par sauvegarde) sont déplacés à côté de `Femme/`, `Homme/`, `Mannequin/`. Les identifiants de dossier n'ont pas changé, donc aucun workflow de fiche n'a été modifié. L'indexation de la bibliothèque **ignore** les dossiers dont le nom contient `VFN` (sinon elle aurait pris les images générées pour des inspirations).
- **`VFN — Sauvegarde (manuelle)`** (`DD9ug6YEISQkIYgP`) : bouton *Execute workflow* dans n8n. Il lit les workflows `VFN…` publiés avec le credential `n8n API` (URL de base `https://178-105-102-54.sslip.io/api/v1`) et les 6 Data Tables, puis écrit dans `VFN Sauvegardes/AAAA-MM-JJ_HHMM/` : `manifest.json`, `data_tables.json` (toutes les lignes), `data_tables_schema.json` (colonnes et types) et un `workflow__<nom>__<id>.json` par workflow (26 workflows, 29 fichiers au total). Les credentials ne sont jamais dans les exports : à recréer si on restaure sur un autre n8n. Pour restaurer : *Import from file* dans n8n pour chaque workflow, recréer les Data Tables d'après le schéma et réinjecter les lignes.
- Les exports JSON ne sont pas synchronisés automatiquement : ils sont à jour au moment où la sauvegarde est lancée. Pour les versionner dans git, télécharger le dossier daté dans `poc-annonces-n8n/workflows/`.

## Étape 9 — refonte coût / mood / texte (2026-09-25)

Référence avant : job `mufe74xl35gs`, mesuré le 2026-09-25 : cout_total=0.5610621, cout_images=0.56076, cout_texte≈0.0003 ; jeu de test : `Test_humain/Gemini/Input` (t-shirt Peggy Sue's, texte visible, photos non commitées).

Script de mesure de coût : `scripts/measure_cost.sh <job_id>` (lit VFN_SECRET depuis `.env` ou l'environnement).

- Colonnes ajoutées (2026-09-25) : library.description_en, library.utilisations ; jobs.marque, taille, mesures, etat, prix, texte_visible, garment_en, mannequin_desc, inspi_texte (JSON [{file_id, nom_fichier, description_en}]).
- Prompts ajoutés le 2026-09-25 (tous inactifs, activation dans les tâches consommatrices) : brief_commun v2, brief_ref_mannequin v2, config_mannequins v2, brief_plan_porte_sans_miroir v1, brief_garment_en v1, brief_inspi_texte v1, config_pastilles v1, texte_fiche v3, indexation_photo v2, config_image v2.
- Indexation en anglais (2026-09-25) : prompt indexation_photo v2 actif (v1 inactif, rollback possible via /prompts/activer) ; le workflow d'indexation écrit la description anglaise (120-180 mots) dans library.description_en avec utilisations = 0 (description laissée vide) ; la réponse de /library/upload renvoie drive_file_ids. Migration unique des descriptions existantes : workflow « VFN — Migrer les descriptions (unique) » (f8NwfsZiJTnKOHO3, déclencheur manuel, idempotent), 23/23 lignes migrées, coût ≈ 0,003 $.
- Formulaire de fiche (2026-09-25) : `POST /job` accepte en plus dans le multipart `marque`, `taille`, `mesures`, `etat`, `prix`, `texte_visible` (`true`/`false`), enregistrés dans `jobs` (chaînes vides par défaut, rétrocompatible). `GET /job-status` renvoie en plus `marque`, `taille`, `mesures`, `etat`, `prix`, `texte_visible` (booléen), `garment_en`, `mannequin_desc`, `inspi_texte` (tableau). `GET /config` renvoie `plans: ["porte_miroir","cintre","detail"]` et `pastilles: [{code, fragment}]` (prompt actif `config_pastilles`, activé v1). `GET /library` renvoie en plus `description_en` et `utilisations` par photo. `scripts/test_job.sh` accepte les variables MARQUE, TAILLE, MESURES, ETAT, PRIX, TEXTE_VISIBLE.
- Texte de fiche (2026-09-25) : prompt texte_fiche v3 actif (v2 inactif, rollback via /prompts/activer). Le modèle renvoie `{description, garment_en}` (plus de titre/mood/questions) ; le titre est un gabarit `<Type> <marque> — taille <taille>` construit par le workflow, la description = texte du modèle + lignes Marque/Taille/Mesures/État issues du formulaire, `garment_en` (anglais, sert aux images) est stocké dans jobs, `questions` = `[]`, `mood` inchangé. Vérifié sur `mufsjqprkf3m` (coût texte ≈ 0,0002 $), affinage OK.
- Style sans LLM et validation à choix humain (2026-09-25) : `POST /job/style` (sous-workflow `FI9HyhPdvbATuSqw`) n'appelle plus de modèle : pool de la bibliothèque filtré par genre/type/moods (comparaison insensible à la casse, repli sur d'autres types), trié par `utilisations` décroissantes, 2 premières en `decor_refs` (vision) et 3 suivantes en `inspi_texte` (texte, avec `description_en`), `mannequin_desc` lu dans `config_mannequins` (clés insensibles à la casse), `avertissements`, statut `en_attente_validation`, coût inchangé. `config_mannequins` v2 (genre → description anglaise) est actif ; v1 (genre → id Drive) reste pour le rollback via `/prompts/activer` ; `mannequin_file_id` est désormais vide. Aucun workflow existant n'a eu besoin d'être rendu tolérant : l'aperçu d'image (`XKXHym7UwzHoh6in`) lit les valeurs dans un try/catch et ignore simplement les textes, les sous-workflows de génération lisent `jobs.mannequin_file_id`. `POST /job/valider` `{job_id, mood, decor_refs?: [file_id] (max 2), inspi_texte?: [file_id] (max 3), garment_en?, mannequin_desc?, texte_visible?}` : 400 si plus de 2/3 ids, id inconnu ou inactif, ou id présent dans les deux listes ; 409 si le job n'est pas `en_attente_validation` ; sinon enregistre, réécrit `inspi_texte` avec les objets relus dans `library`, incrémente `library.utilisations` de chaque inspiration retenue, passe en `generation_en_cours` et lance la génération.
- Génération à 3 plans sans check ni retry (2026-09-25) : prompts activés brief_commun v2, brief_ref_mannequin v2 (mannequin décrit en texte), brief_plan_porte_sans_miroir v1, brief_garment_en v1, brief_inspi_texte v1 (v1 précédents inactifs, rollback via `/prompts/activer`) ; `config_image` inchangé (1K). Plans : `porte_miroir`, `cintre`, `detail` (plus de `a_plat` dans le lanceur renommé `VFN — Générer les 3 plans (sous-workflow)`, `Générer un plan`, `/job/plan`, `/job/feedback`, `/job-status`). Une seule tentative par plan : le check de fidélité (LLM vision) et le retry automatique sont supprimés ; la ligne `shots` porte `fidelite_ok = false`, `fidelite_verifiee = false`, `cout` = coût image seul, `brief` = prompt exact. Images envoyées : photos du vêtement puis 2 inspirations `decor_refs` (vision), jamais de mannequin ; le brief ajoute `garment_en`, les inspirations `inspi_texte` (description anglaise, 3 max) et, pour `porte_miroir` seulement, `mannequin_desc`. Si `texte_visible`, le plan `porte_miroir` utilise le brief `porte_sans_miroir` (photo prise par un tiers, texte lisible non inversé) ; l'identifiant du plan reste `porte_miroir`. `texte_visible` est lu comme vrai pour `true` ou `1` (la table renvoie `1` après écriture booléenne par `/job/valider`). `log.json` contient en plus `formulaire`, `garment_en`, `inspi_texte`, `mannequin_desc`, `texte_visible`. Test réel sur `mufsjqprkf3m` (mood `vintage_retro`) : 3 plans en 1 tentative chacun via Fal, `cout_images` 0,24 $ (0,08 $/image à 1K), `cout_texte` 0,00045 $, galerie prête en ~1 min 30 ; `porte_miroir` régénéré une fois (0,08 $) après correction de la lecture de `texte_visible`, soit 0,32 $ d'images au total pour ce job.
- Pastilles d'ajustement à la régénération (2026-09-25) : `POST /job/plan` accepte en plus `pastilles: [code, ...]` (optionnel, avec `feedback` libre optionnel ; les deux vides = régénération simple). Codes autorisés (prompt actif `config_pastilles`, lus à chaque appel) : `trop_sombre`, `trop_sature`, `couleur_fausse`, `vetement_deforme`, `trop_mis_en_scene`, `piece_trop_rangee`. Les fragments sont concaténés puis la consigne libre, et passés en `extra` au brief (bloc « Extra instructions from the seller ») ; ils sont aussi enregistrés dans le commentaire du signal négatif implicite. Code inconnu : HTTP 400 `{error, autorisees}` avant tout changement de statut ni coût. Vérifié sur `mufsjqprkf3m` (`cintre` + `trop_sature`) : le brief contient « Reduce colour saturation: more muted and natural colours. » ; coût de cette régénération 0,08 $ (cout_images 0,32 → 0,40 $). `scripts/measure_cost.sh` lit maintenant `cout_plan` par plan.
- Front (2026-09-25, `front/index.html`) : **formulaire** avec marque, taille, mesures, état (suggestions Vinted), prix et case « texte ou logo lisible » (`texte_visible` = `"true"`/`"false"`), plus de choix de moods à la création (`moods_autorises` = tous). **Texte** : bloc « Questions du modèle » supprimé, feedback renommé « Feedback sur le texte », `garment_en` éditable (même brouillon que l'écran de relecture). **Style** : chips de moods de `/config` (un seul mood = mood de la fiche, qui filtre aussi la grille ; second clic = aucun filtre), grille des photos actives de `GET /library` du genre (insensible à la casse) et du type de la fiche (case « Tous les types » pour élargir), triée par `utilisations` décroissantes, avec boutons exclusifs « Vision » (2 max) / « Texte » (3 max) et « Utiliser comme inspi pour la génération » (vision si place, sinon texte) ; présélection = `decor_refs` / `inspi_texte` au premier affichage de la fiche en `en_attente_validation` seulement (les rafraîchissements n'écrasent pas la sélection) ; dépôt d'une nouvelle inspiration depuis la fiche (`/library/upload`, les `drive_file_ids` renvoyés entrent dans la sélection, grille rechargée 20 s après). **Écran « Ce que l'IA va voir »** : `garment_en`, `mannequin_desc` (textareas), 2 miniatures vision, descriptions anglaises des inspirations texte (tronquées, « voir tout »), mood en liste fermée, case « Photo portée : sans miroir » préréglée sur `texte_visible` ; « Générer les 3 photos » (~0,25 $) appelle `POST /job/valider`, les 400 s'affichent en toast. **Galerie** : 3 plans (Porté, Sur cintre, Détail), plus aucune mention de fidélité, photo d'origine à gauche et image générée à droite, pastilles (`/config.pastilles`) + consigne libre envoyées à `POST /job/plan`, étalonnage côté front à l'affichage et au téléchargement (constante `GRADE` en tête du script : saturate 0,82, sepia 0,10, contrast 0,97, brightness 1,02, grain 60 000 points à 6 %, JPEG 0,92 ; repli pixel par pixel si le canvas ne gère pas `ctx.filter`), bouton « Voir brut ». Photo d'origine : aucun endpoint ne sert les photos d'entrée d'une fiche (`/job-status` ne les liste pas et `/image` les refuse), le front garde donc la 1re photo en mémoire pour une fiche créée dans la session et l'omet sinon. Les images téléchargées restent celles de `/image` (jpeg réduit à 1000 px). Vérifié dans le navigateur intégré sans appel payant : galerie de `mufsjqprkf3m`, et fiche de test `muftpawvta7x` (Peggy Sue's) menée jusqu'à l'écran de relecture, laissée en `en_attente_validation`.
- **Photos d'origine côte à côte** : `GET /job-status` renvoie `input_photo_ids` (ids Drive des images du `drive_input_folder_id` du job, triées par nom ; `[]` si dossier absent ou erreur Drive, sans casser la réponse ; un listage Drive par poll). `GET /image` accepte en plus tout id dont le parent Drive (API `files/{id}?fields=parents`) est le `drive_input_folder_id` d'un job de la table, fichier image non supprimé ; les autres ids restent en 404. Vérifié sur `mufsjqprkf3m` : 3 ids, jpeg 200, id aléatoire 404, sans en-tête 403. Le front affiche `input_photo_ids[0]` à gauche de chaque plan (repli sur la photo en mémoire si la liste est vide).
- Test de basse résolution (2026-09-25, mesure sans décision) : Fal `nano-banana-2/edit` accepte `resolution` = 0.5K, 1K, 2K, 4K ; prix Fal 0,08 $ à 1K, multiplicateurs 0.5K = 0,75x (0,06 $), 2K = 1,5x, 4K = 2x (page du modèle sur fal.ai). Le sous-workflow multiplie déjà par les unités facturées : à 0.5K le coût enregistré est 0,75 x `fal_cost_per_unit_usd`, donc laisser `fal_cost_per_unit_usd` à 0,08 (la version 3 de test le met à 0,06 par erreur, coût enregistré 0,045 $ au lieu de 0,06 $ réel). Test sur `mufsjqprkf3m`, plan `cintre` : image 448x592 px à 0.5K contre 747x1000 px pour la version 1K. v1 (1K) actif en attendant décision ; config_image v3 = basse résolution (0.5K) prête à activer (v2 = copie de v1, inchangée ; l'outil MCP ne permet pas de modifier une ligne, d'où une v3 ajoutée).

### Étape 9 — résultat de bout en bout, coûts, décisions, limites (2026-09-25)

- **Test de bout en bout par le front** (fiche `muftpawvta7x`, t-shirt Peggy Sue's, mood `vintage_retro`, 2 inspirations vision + 2 inspirations texte via « Tous les types », « Générer les 3 photos » cliqué une fois) : `galerie_prete` en ~25 s, 3 plans en 1 tentative chacun (Fal, 0,08 $ l'image), aucune donnée de fidélité, `log.json` présent dans le dossier Drive du job (`drive_log_file_id`). Les briefs (`shots.brief`) contiennent `garment_en` et le bloc des inspirations texte ; `porte_miroir` utilise la variante sans miroir (texte lisible non inversé) et contient la description du mannequin ; `cintre` et `detail` n'en contiennent aucune. `library.utilisations` a été incrémentée pour les 4 inspirations retenues. Galerie : photo d'origine à gauche, image étalonnée à droite, « Voir brut » fonctionne, 6 pastilles visibles.
- **Coûts** : comparaison à périmètre égal, sans régénération : 0,40 $ (job `mufe74xl35gs`, 4 premiers plans, dont un retry de fidélité = 5 images) → 0,24 $ (job `muftpawvta7x`, 3 images à 0,08 $, `cout_texte` 0,0002003 $), soit -40 %. Les chiffres 0,5610621 $ → 0,2402003 $ (-57 %) comparent un job avec régénérations (`mufe74xl35gs` : 0,56 $ après 2 tentatives d'un `detail` régénéré, 7 images à ≈ 0,08 $) à un job sans régénération : ils ne sont pas à périmètre égal. **La cible du cahier des charges (< 0,20 $ par fiche sans régénération) n'est pas atteinte à 1K** : 0,24 $ = 3 × 0,08 $. Les seuls leviers restants sont le 0.5K (rejeté, voir ci-dessous ; prix à 0,75x) ou un modèle moins cher.
- **Résolution : le 0.5K est rejeté.** Le texte imprimé se dégrade à 0.5K et Fal facture 0,75x, soit une économie trop faible. Production reste en 1K. État de `config_image` (vérifié via `GET /prompts`) : v1 actif (1K, 0,08 $) ; v2 inactif, même contenu que v1 (1K, 0,08 $, note « refonte coût/mood ») ; v3 inactif, 0.5K avec `fal_cost_per_unit_usd` 0,06 (erroné : le sous-workflow multiplie déjà par les unités facturées, ne pas réutiliser).
- **Limites connues / restes à faire** :
  - `meta_ajustement` v1 décrit encore 4 photos et un check de fidélité.
  - Le workflow de proposition de prompts `5K6sfWDDQVc8NpI4` : son signal de dérive de fidélité est désormais toujours vide.
  - Le workflow Garder `TrqnPOfRw7NLEEzz` accepte encore `a_plat`.
  - `/job-status` fait un listage Drive par poll (pour `input_photo_ids`).
  - Fichiers de test laissés dans Drive/bibliothèque : photos inactives `1AAsnk4COM1pf6iXF-kWEr8ay1x9PLVVz` et `1Q5vOu3QGvu0be-Ju3Wp1qCHlpBotqueY` (genre en minuscules).
  - Ligne de feedback implicite 👎 sur le job `mufsjqprkf3m`, plan `porte_miroir`, issue de la régénération de test.
  - Jobs de test créés à l'étape 9 à supprimer de la table `jobs` via l'UI n8n : `mufsg4szpyuj`, `mufsgkl0io7i`, `mufsjqprkf3m`, `muftpawvta7x` (et tout autre job de test).
  - L'étalonnage n'est appliqué que côté front : les fichiers Drive restent bruts.
  - CORS : l'en-tête `Access-Control-Allow-Origin` de `/image` est mis en cache par URL sans `Vary: Origin` côté serveur ; ouvrir le front depuis deux origines différentes (`localhost` puis `127.0.0.1`) fait échouer les images déjà chargées depuis l'autre origine. Utiliser une seule origine.
  - Sauvegarde : `VFN — Sauvegarde (manuelle)` (`DD9ug6YEISQkIYgP`) n'a pas de version publiée, donc `execute_workflow` en mode production est refusé ; en mode manuel, l'exécution 569 est restée « running » sans exécuter de nœud (déclencheur manuel en attente). À lancer depuis l'UI n8n (bouton « Sauvegarder maintenant »).

## Référence des workflows n8n (audit de l'instance, 2026-09-25)

Relevé fait directement sur l'instance n8n (nœuds, connexions, code, tables, exécutions), pas depuis cette doc. **28 workflows** au départ : 26 publiés, 2 inactifs (Sauvegarde, Migration). Le n°28 a été **archivé le 2026-09-25** : il reste **27 workflows, dont 26 publiés et 1 inactif** (Sauvegarde). Tous préfixés `VFN —`. Un seul secret protège tous les webhooks (header `X-VFN-Secret`, credential `VFN webhook secret`). Modèles : `google/gemini-2.5-flash-lite` (texte, vision) et Fal `nano-banana-2/edit` (images, repli OpenRouter) ; prompts lus à chaque exécution dans la table `prompts` (version active la plus haute).

Tables : `jobs` (une ligne par fiche), `shots` (une ligne par image générée ou échec), `feedback` (pouces, notes, signaux implicites), `prompts` (versions), `library` (photos d'inspiration), `users` (profils).

### Vue d'ensemble

| # | Workflow | Type | ID | Appelé par | Verdict audit |
|---|---|---|---|---|---|
| 1 | Créer une fiche | webhook `POST /job` | `5erMviLZ0qLPtd1E` | front | garder |
| 2 | Générer le texte | sous-workflow | `gdGJLLnGtW79Jeol` | 1, 3 | garder |
| 3 | Affiner le texte | webhook `POST /job/texte` | `bRdAbgJiiGKwNyvP` | front | garder |
| 4 | Lire une fiche (statut) | webhook `GET /job-status` | `3EkEko4Qo2ofd7LK` | front (polling) | garder, à alléger |
| 5 | Choisir le style | webhook `POST /job/style` | `ao81dPakf9IqTIyr` | front | garder |
| 6 | Sélectionner le style | sous-workflow | `FI9HyhPdvbATuSqw` | 5 | fusionnable dans 5 |
| 7 | Valider le plan | webhook `POST /job/valider` | `z1SY3ZkptHVSd4al` | front | garder |
| 8 | Générer les 3 plans | sous-workflow | `9Y0O9Z4MO9wVM0xB` | 7 | garder |
| 9 | Générer un plan | sous-workflow | `HKMVyeJJQTSoBN6X` | 8, 11 | fusionnable avec 10 |
| 10 | Tentative image | sous-workflow | `pGvWMH08Go4yGJYp` | 9 | garder |
| 11 | Régénérer un plan | webhook `POST /job/plan` | `MIeRXvNz9a4cwKIo` | front | garder |
| 12 | Garder un plan | webhook `POST /job/garder` | `TrqnPOfRw7NLEEzz` | front | garder |
| 13 | Feedback | webhook `POST /job/feedback` | `DgoKnyLMpuLqabFh` | front | garder |
| 14 | Écrire le journal Drive | sous-workflow | `LtGZGU42Lkx2ip3u` | 9, 13 | garder |
| 15 | Indexation bibliothèque | manuel + webhook + sous-workflow | `k7j9FcAjqQKLYCj1` | 18 | garder |
| 16 | Lire la bibliothèque | webhook `GET /library` | `g1m9isMxo3gWGuV3` | front | garder |
| 17 | Modifier une photo de la bibliothèque | webhook `POST /library/update` | `kNGZI3ZZSRlckkgP` | front | garder |
| 18 | Ajouter des inspirations | webhook `POST /library/upload` | `a6h3K0SfbhFY4cBp` | front | garder |
| 19 | Aperçu d'une image Drive | webhook `GET /image` | `XKXHym7UwzHoh6in` | front | garder, à corriger |
| 20 | Configuration pour le front | webhook `GET /config` | `fES1vA8Ak6Vz9N6K` | front | garder |
| 21 | Lister les prompts | webhook `GET /prompts` | `nqG841Bhc9LJWE66` | front | garder |
| 22 | Activer une version de prompt | webhook `POST /prompts/activer` | `GBUtNGync3iN147g` | front | garder |
| 23 | Proposer un ajustement de prompt | webhook `POST /prompts/propose` | `5K6sfWDDQVc8NpI4` | front | garder |
| 24 | Lire le profil user | webhook `GET /users/profil` | `CgSPgAdmyCA356HI` | front | garder |
| 25 | Enregistrer le profil user | webhook `POST /users/profil` | `AT3l77KOj11xSIuV` | front | garder |
| 26 | Proposer une mise à jour du profil | webhook `POST /users/profil/propose` | `PHlT76TnZbViAFlw` | front | garder |
| 27 | Sauvegarde (manuelle) | manuel, inactif | `DD9ug6YEISQkIYgP` | UI n8n | garder |
| 28 | Migrer les descriptions (unique) | manuel, inactif | `f8NwfsZiJTnKOHO3` | — | **archivé le 2026-09-25** (restaurable depuis l'UI n8n) |

### Chaîne d'appels d'une fiche

```
front ─ POST /job ─▶ [1 Créer] ─▶ [2 Texte] ─▶ statut texte_pret
front ─ POST /job/texte ─▶ [3 Affiner] ─▶ [2 Texte]
front ─ POST /job/style ─▶ [5 Choisir le style] ─▶ [6 Sélectionner] ─▶ en_attente_validation
front ─ POST /job/valider ─▶ [7 Valider] ─▶ [8 3 plans] ─▶ 3 × [9 Un plan] ─▶ [10 Tentative image]
                                                             └▶ [14 Journal] quand les 3 plans sont là
front ─ POST /job/plan ─▶ [11 Régénérer] ─▶ [9 Un plan] ─▶ [10 Tentative image]
front ─ GET /job-status ─▶ [4 Statut]   (polling)
front ─ POST /job/feedback ─▶ [13 Feedback] ─▶ [14 Journal]
```

Statuts d'un job : `texte_en_cours` → `texte_pret` → `selection_en_cours` → `en_attente_validation` → `generation_en_cours` → `galerie_prete` (ou `budget_depasse`) → `termine` ; `erreur` possible aux étapes texte et sélection.

### Fiche : création, texte

**1. Créer une fiche** (`5erMviLZ0qLPtd1E`, `POST /webhook/vfn/job`)
- Entrée : multipart `user`, `genre`, `type_vetement`, `moods_autorises` (JSON), `marque`, `taille`, `mesures`, `etat`, `prix`, `texte_visible`, photos `photo0`, `photo1`…
- Étapes : `Préparer le job` (valide, génère `job_id` = horodatage base 36 + 4 caractères) → crée le dossier Drive `<date>_<job_id>` sous `VFN Fiches` puis son sous-dossier `input` → insère la ligne `jobs` (statut `texte_en_cours`) → **répond `{job_id}`** → éclate les photos (`photo_1.ext`…) → les envoie dans `input` → appelle le sous-workflow 2.
- La réponse part après l'écriture du job (sinon le premier poll donnait 404), avant l'envoi des photos.
- Écrit : `jobs`, Drive. Échec : `Préparer le job` lève une erreur (400 côté client) si aucune photo ou `user` manquant.

**2. Générer le texte** (`gdGJLLnGtW79Jeol`, sous-workflow, entrée `job_id`)
- Lit le job, tous les prompts, le user, tout le feedback et toute la table `jobs` (pour choisir des exemples approuvés).
- Télécharge les photos du dossier `input`, les réduit à 1280 px (JPEG 88).
- `Construire la requête texte` : prompt actif `texte_fiche` avec `{profil}` (préférences du user, tronquées à `config_profil.max_chars`) et `{exemples}` (jusqu'à `nb_exemples` fiches déjà notées 👍 sur la description, même genre et type en priorité) ; ajoute l'historique (`historique`) pour l'affinage.
- Appel OpenRouter (JSON strict `{description, garment_en}`, timeout 120 s). Sortie erreur → `Marquer le job en erreur` (statut `erreur`).
- `Traiter la réponse` : répare le JSON s'il contient des retours ligne bruts, construit le titre `<Type> <marque> — taille <taille>`, ajoute les lignes Marque/Taille/Mesures/État à la description, ajoute la réponse à `historique`, cumule le coût dans `cout_total`, mémorise la version du prompt (`prompt_versions`). Met à jour `jobs` : statut `texte_pret`.
- `garment_en` (anglais) sert ensuite aux prompts image.

**3. Affiner le texte** (`bRdAbgJiiGKwNyvP`, `POST /job/texte` `{job_id, message}`)
- 404 si job inconnu. Erreur si `message` vide ou si une génération de texte est déjà en cours. Ajoute `{role:"user"}` à `historique`, statut `texte_en_cours`, **répond**, puis relance le sous-workflow 2.

**4. Lire une fiche (statut)** (`3EkEko4Qo2ofd7LK`, `GET /job-status?id=`)
- Lit le job, ses `shots`, son `feedback`, **et liste le dossier Drive `input`** (pour `input_photo_ids`). Assemble une réponse unique : formulaire, titre, description, `garment_en`, mood, `decor_refs`, `inspi_texte`, `mannequin_desc`, avertissements, 3 plans (statut `en_attente`/`pret`/`erreur`, tentative courante, `drive_file_id`, fournisseur, coût, `garde`), feedback par cible, coûts (texte, images, total), erreur, `drive_folder_id`.
- 404 si job inconnu. C'est l'endpoint le plus appelé (polling toutes les 4 s environ).

### Fiche : style et validation

**5. Choisir le style** (`ao81dPakf9IqTIyr`, `POST /job/style` `{job_id, moods_autorises?}`)
- 409 si le job n'est pas `texte_pret`, `en_attente_validation` ou `erreur`. Enregistre `moods_autorises`, statut `selection_en_cours`, **répond**, lance le sous-workflow 6. Sert aussi à « retirer au sort ».

**6. Sélectionner le style** (`FI9HyhPdvbATuSqw`, sous-workflow, **aucun appel de modèle**)
- Lit job, bibliothèque, prompts. Filtre `library` (actif, même genre et type, moods autorisés ; à défaut même genre sans le type, avec avertissement ; sinon rien), trie par `utilisations` décroissantes, met les 2 premières en `decor_refs` (vision) et les 3 suivantes en `inspi_texte` (texte, avec `description_en`), lit `mannequin_desc` du genre dans `config_mannequins`, écrit `avertissements`, statut `en_attente_validation`. Un seul nœud de code plus des lectures : candidat à l'inlining dans 5.
- Reste mort : `mannequin_file_id` (toujours vide).

**7. Valider le plan** (`z1SY3ZkptHVSd4al`, `POST /job/valider` `{job_id, mood?, decor_refs?[≤2], inspi_texte?[≤3], garment_en?, mannequin_desc?, texte_visible?}`)
- 409 si le job n'est pas `en_attente_validation`. 400 si plus de 2/3 ids, id inconnu ou inactif, ou id dans les deux listes. Enregistre, statut `generation_en_cours`, **répond**, puis en parallèle : lance le sous-workflow 8 (sans attendre) et incrémente `library.utilisations` de chaque inspiration retenue.

### Fiche : génération des photos

**8. Générer les 3 plans** (`9Y0O9Z4MO9wVM0xB`, sous-workflow)
- Crée le sous-dossier Drive `output`, enregistre `drive_output_folder_id`, statut `generation_en_cours`, puis lance **3 exécutions du workflow 9** en parallèle et sans attendre : `porte_miroir`, `cintre`, `detail`.

**9. Générer un plan** (`HKMVyeJJQTSoBN6X`, sous-workflow `{job_id, plan, feedback, force}`)
- Appelle le workflow 10, relit les `shots`, et si les 3 plans ont une ligne courante : statut `galerie_prete` (ou `budget_depasse` si l'un d'eux est en échec de plafond), puis lance l'écriture du journal (14) sans attendre. Le dernier des 3 qui termine voit les 3 lignes et fait la bascule.

**10. Tentative image** (`pGvWMH08Go4yGJYp`, sous-workflow `{job_id, plan, extra, force}`) : le cœur de la génération.
- Lit job, prompts, shots, liste les photos d'origine. `Préparer la tentative` : numéro de tentative, coût déjà dépensé, **plafond** (`config_plafond` : refuse si dépense + estimation dépasse le plafond, sauf `force`), assemble les briefs (`brief_commun`, `brief_ref_vetement`, `brief_ref_decor`, `brief_garment_en`, `brief_inspi_texte`, `brief_ref_mannequin` pour `porte_miroir` seulement, `brief_plan_<plan>` ou `brief_plan_porte_sans_miroir` si `texte_visible`).
- Télécharge et réduit à 1024 px les photos du vêtement puis les 2 inspirations vision, construit le prompt, appelle Fal (`fal.run/<fal_model>`, 300 s). Codes 402/403 → repli OpenRouter ; autre erreur → échec consigné.
- Image reçue → Drive (`<plan>_<tentative>.png` dans `output`) → ligne `shots` (`courant = true`, `garde = true`, coût, fournisseur, `brief` exact) → les anciennes tentatives du plan passent `courant = false`. Échec → ligne `shots` avec `erreur`.
- Une seule tentative, pas de check de fidélité ni de retry. Vestiges : champs `retry_needed`, `problemes`, `photo_urls`, colonnes `fidelite_*`.

**11. Régénérer un plan** (`MIeRXvNz9a4cwKIo`, `POST /job/plan` `{job_id, plan, pastilles?, feedback?, force?}`)
- 409 si le job n'est pas `galerie_prete`/`budget_depasse` ou plan inconnu. 400 si pastille inconnue (liste `config_pastilles`). Concatène fragments de pastilles + consigne libre, statut `generation_en_cours`, enregistre un 👎 implicite (`feedback.implicite = true`), **répond**, lance le workflow 9.

**12. Garder un plan** (`TrqnPOfRw7NLEEzz`, `POST /job/garder` `{job_id, plan, garde: bool}`)
- Met à jour `shots.garde` sur la ligne courante du plan. 409 si job pas prêt, `garde` non booléen ou plan inconnu. Accepte encore `a_plat` (plan supprimé).

### Fiche : feedback et journal

**13. Feedback** (`DgoKnyLMpuLqabFh`, `POST /job/feedback` `{job_id, cible, note, raisons?, commentaire?}`)
- `cible` : `description`, `plan:<porte_miroir|cintre|detail>` ou `global`. `note` : `up`/`down` (ou 👍/👎). `raisons` validées contre `config_feedback` (400 avec la liste autorisée). 409 si on note un plan avant la galerie. Upsert dans `feedback` (une note par job et cible). `global` : statut `termine`. Lance le journal (14) sans attendre.

**14. Écrire le journal Drive** (`LtGZGU42Lkx2ip3u`, sous-workflow `{job_id}`)
- Construit `log.json` (entrées, formulaire, texte, style, prompts utilisés, tous les `shots` avec brief et coût, feedback, coûts) et le crée ou le met à jour dans le dossier Drive du job ; mémorise `drive_log_file_id`.

### Bibliothèque d'inspirations

**15. Indexation bibliothèque** (`k7j9FcAjqQKLYCj1`)
- Trois déclencheurs : manuel, `POST /library/reindex` (jamais appelé par le front), sous-workflow (appelé par 18). Parcourt le Drive en 3 requêtes (genres, types, photos), ignore `Mannequin/*` et les photos déjà dans `library`, **maximum 100 par exécution**, réduit à 1024 px, envoie à Gemini (prompt `indexation_photo` + liste `moods_liste`, JSON strict `{description (anglais), tags, moods ≤3}`), insère une ligne `library` (`source = import_initial`). Racine Drive codée en dur dans le nœud `Préparer la configuration`. ~0,0003 $ par photo.

**16. Lire la bibliothèque** (`g1m9isMxo3gWGuV3`, `GET /library`) : toute la table `library` triée genre/type/nom.

**17. Modifier une photo** (`kNGZI3ZZSRlckkgP`, `POST /library/update` `{drive_file_id, moods?, tags?, actif?}`) : 404 si inconnue ; moods validés contre `moods_liste` (max 3), tags max 12, `actif` booléen.

**18. Ajouter des inspirations** (`a6h3K0SfbhFY4cBp`, `POST /library/upload`, multipart `genre`, `type_vetement`, photos) : valide (genre femme/homme, type ≤ 40 caractères, fichiers image), trouve ou crée le dossier du type sous le genre (ids des dossiers genre codés en dur), envoie `insp_<stamp>_<n>.ext`, **répond**, puis lance l'indexation (15) sans attendre.

**19. Aperçu d'une image Drive** (`XKXHym7UwzHoh6in`, `GET /image?id=`)
- N'accepte que les ids connus : `library`, `shots`, descriptions de mannequin héritées, ou fichier image dont le parent Drive est le `drive_input_folder_id` d'un job. Sinon 404. Télécharge, réduit à 1000 px (JPEG 82), sert avec `Cache-Control: private, max-age=3600`.
- **À corriger** : à chaque image il relit **toute la table `jobs`**, toute `library` filtrée, `shots` filtrée et fait un appel Drive de métadonnées, même pour un id de bibliothèque déjà autorisé.

### Configuration, prompts, profil

**20. Configuration pour le front** (`fES1vA8Ak6Vz9N6K`, `GET /config`) : moods (liste `id`/définition), users, genres, types par genre (déduits de `library`), plans, pastilles, raisons de feedback, plafond en $. Sert aussi de test de secret au front.

**21. Lister les prompts** (`nqG841Bhc9LJWE66`, `GET /prompts`) : tous les prompts groupés par nom avec versions, `actif`, notes, date, et `ajustable` (faux pour `config_*`, `moods_liste`, `meta_ajustement`).

**22. Activer une version** (`GBUtNGync3iN147g`, `POST /prompts/activer` `{nom, version}`) : 404 si inconnue ; désactive toutes les versions du nom puis active celle-là (sert aussi au rollback).

**23. Proposer un ajustement de prompt** (`5K6sfWDDQVc8NpI4`, `POST /prompts/propose` `{nom, jours?}`) : refuse les `config_*`, `moods_liste`, `meta_ajustement`. Rassemble sur la période feedbacks, régénérations implicites, corrections de texte, dérives de fidélité, répond « pas assez de signaux » sous `min_signaux`. Sinon demande à `config_ajustement.modele` une nouvelle version, rejette la proposition si les jetons `{...}` changent, calcule un diff, **enregistre une version inactive** (jamais activée seule), renvoie résumé, confiance, diff, coût. Le signal de fidélité est toujours vide depuis l'étape 9 ; le nœud Telegram a été retiré mais le texte `telegram_text` est encore construit.

**24. Lire le profil** (`CgSPgAdmyCA356HI`, `GET /users/profil?user=`) : `preferences_md` et `max_chars`. 404 si user inconnu.

**25. Enregistrer le profil** (`AT3l77KOj11xSIuV`, `POST /users/profil` `{user, preferences_md}`) : 400 si texte trop long (`config_profil.max_chars`).

**26. Proposer une mise à jour du profil** (`PHlT76TnZbViAFlw`, `POST /users/profil/propose` `{user, jours?}`) : à partir des corrections de texte et avis 👎/commentaires de ce user, propose un profil révisé (jamais appliqué automatiquement). « Pas assez de retours » sinon.

### Maintenance

**27. Sauvegarde (manuelle)** (`DD9ug6YEISQkIYgP`, inactif) : exporte les workflows `VFN…` **actifs seulement** et les 6 tables en JSON (avec schéma) dans un dossier Drive daté `VFN Sauvegardes/<date>`. L'exécution 569 (2026-09-24 18:00) est en **succès** en 77 s : la note « exécution restée running » plus haut dans ce fichier est périmée. Aucune planification.

**28. Migrer les descriptions (unique)** (`f8NwfsZiJTnKOHO3`, inactif, sans description) : traduisait en anglais les descriptions de `library` sans `description_en`. Migration terminée à l'étape 9, plus jamais utile.

### Audit : à supprimer

- **Archivé** : n°28 (migration unique déjà exécutée, inactive, sans description). Aucun autre workflow ne l'appelait.
- Rien d'autre n'est mort : les 26 workflows publiés sont tous appelés par le front ou par un autre workflow. Seul le déclencheur `POST /library/reindex` du n°15 n'est pas utilisé (le manuel et l'appel par 18 suffisent), sans conséquence.

### Audit : fusions possibles (aucune urgence)

| Fusion | Gain | Remarque |
|---|---|---|
| 9 dans 10 | -1 workflow, -1 niveau d'imbrication | 9 n'est plus qu'un enrobage de 10 depuis la suppression du retry |
| 6 dans 5 | -1 workflow | 6 n'appelle plus de modèle, un nœud de code |
| 24+25, 21+22, 16+17 (2 déclencheurs webhook par workflow, même chemin, méthodes différentes) | -3 workflows | seulement si on veut moins de workflows ; aucun gain fonctionnel |

### Audit : points de robustesse et de performance

1. **Fiche coincée en `generation_en_cours`** : aucun workflow d'erreur n'est configuré. Une exception dans le sous-workflow 10 (ex. « Aucune photo dans le dossier input », Drive indisponible) laisse le job dans son statut pour toujours. Seuls les échecs de modèle ou de Fal sont consignés dans `shots`. À traiter par un workflow d'erreur global qui passe le job en `erreur`.
2. **Polling coûteux** : n°4 fait 3 lectures de tables et **1 listage Drive par poll** (il représente la grande majorité des 200 dernières exécutions avec n°19). Stocker `input_photo_ids` dans `jobs` à la création supprime l'appel Drive.
3. **Lectures complètes de tables** : n°19 lit toute la table `jobs` à chaque image, n°2 lit toute `jobs` et tout `feedback` à chaque génération de texte, n°23 et n°26 lisent tout. Sans impact aujourd'hui, croît avec l'historique.
4. **Aucun endpoint de liste des jobs** : nécessaire pour la vue historique (à créer).
5. **Valeurs codées en dur** : racine de la bibliothèque et modèle `gemini-2.5-flash-lite` (n°15, n°2), ids des dossiers genre (n°18), racine de `VFN Fiches` (n°1) ; `config_ajustement.modele` existe déjà pour n°23/26.
6. **Secret dans le front** : un seul secret partagé, présent dans le navigateur ; CORS ouvert (`*`). Acceptable pour un usage à deux, à connaître.
7. **Sauvegarde** : manuelle, n'exporte que les workflows actifs (donc pas n°27, qui est inactif) et aucune planification.
8. **Vestiges à nettoyer** : `a_plat` (n°12), `mannequin_file_id`, colonnes `shots.fidelite_*`, champs `retry_needed`/`problemes`, `telegram_text` et `chat_id` (n°23), `meta_ajustement` v1 qui décrit encore 4 photos et un check de fidélité.
9. **Documentation périmée** : l'en-tête de l'étape 4 parle de « 4 plans » et l'étape 3 de jugement LLM ; l'état réel est 3 plans, sélection sans LLM (le workflow 8 s'appelle maintenant `Générer les 3 plans`).

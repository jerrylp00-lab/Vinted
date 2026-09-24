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

Tests réalisés : (1) sous-workflow sur un job de test (`test1`) : 8 s, 0,0002 $, puis affinage avec un message utilisateur (marque et taille intégrées) ; (2) de bout en bout via `scripts/test_job.sh` avec 3 vraies photos (`VFN_SECRET=... ./scripts/test_job.sh femme haut photo1.png …`) : job créé, photos envoyées sur Drive, texte prêt en ~15 s pour 0,0002 $. La réponse `{job_id}` du webhook de création n'est renvoyée qu'après l'écriture du job, sinon le premier poll du statut tombait sur un 404.

Reste : les lignes de test de la table `jobs` (`test1` et deux jobs de `test_job.sh`) sont à supprimer depuis l'UI n8n ; `decor_refs` est vide jusqu'à l'étape 3.

## Étape 3 — Sélection du style et validation (2026-09-24)

| Workflow | ID | Rôle |
|---|---|---|
| `VFN — Sélectionner le style (sous-workflow)` | `FI9HyhPdvbATuSqw` | Filtre `library` (actif, même genre et type, moods autorisés ; à défaut même genre et moods avec avertissement ; sinon aucune référence), tire jusqu'à 10 candidates, jugement visuel du LLM (`selection_style`) qui en garde 2 à 3 et dérive le mood, associe le mannequin du genre (`config_mannequins`). Statut → `en_attente_validation`. |
| `VFN — Choisir le style (webhook)` | `ao81dPakf9IqTIyr` | `POST /webhook/vfn/job/style` `{job_id, moods_autorises?: [...]}` : lance ou relance la sélection (statuts acceptés : `texte_pret`, `en_attente_validation`, `erreur`). Sert aussi de « retirer au sort ». |
| `VFN — Valider le plan (webhook)` | `z1SY3ZkptHVSd4al` | `POST /webhook/vfn/job/valider` `{job_id, mood?, decor_refs?: [file_id, ...]}` : applique les corrections (les ids doivent exister et être actifs dans `library`), statut → `generation_en_cours`. 409 si le job n'est pas `en_attente_validation`. **Ne déclenche pas encore la génération (étape 4).** |

Nouveaux champs de `jobs` : `avertissements` (JSON, ex. « pas de mannequin pour ce genre »), `mannequin_file_id`. `decor_refs` est une liste JSON d'objets `{file_id, nom_fichier, type_vetement, moods, tags}`. Nouveaux prompts : `selection_style` v1 et `config_mannequins` v1 (JSON genre → id de fichier Drive du mannequin, modifiable dans la table). Le statut (`GET /job-status`) renvoie maintenant aussi `mannequin_file_id` et `avertissements`.

Tests (en production, avec le secret) : sélection sur un job `femme/veste` restreint aux moods `urbain_minimaliste` et `streetwear_decontracte` → 2 références cohérentes en ~10 s pour 0,0001 $ ; validation avec mood et référence corrigés → statut `generation_en_cours`, corrections appliquées ; seconde validation → 409.

Le front devra afficher les images de `decor_refs` : il faudra un endpoint d'aperçu des photos Drive (étape 6), les fichiers n'étant pas publics.

## Étape 4 — Génération des 4 plans (2026-09-24)

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

| Workflow | ID | Rôle |
|---|---|---|
| `VFN — Feedback (webhook)` | `DgoKnyLMpuLqabFh` | `POST /webhook/vfn/job/feedback` `{job_id, cible, note, raisons?, commentaire?}`. `cible` : `description`, `plan:<porte_miroir\|a_plat\|cintre\|detail>` ou `global` (note finale). `note` : `up` / `down` (stockée 👍 / 👎). Un nouvel avis sur la même cible **remplace** le précédent (les régénérations, signal implicite, restent en lignes séparées). Les `raisons` doivent appartenir au vocabulaire de la cible (ligne `config_feedback` de `prompts`, modifiable) sinon 400 avec la liste autorisée ; 404 si le job n'existe pas ; 409 pour un avis sur un plan avant que la galerie soit prête. La note `global` passe le job à `termine` et écrit le journal. |
| `VFN — Garder un plan (webhook)` | `TrqnPOfRw7NLEEzz` | `POST /webhook/vfn/job/garder` `{job_id, plan, garde: true/false}` : coche ou décoche « Garder » sur le plan courant. |
| `VFN — Écrire le journal Drive (sous-workflow)` | `LtGZGU42Lkx2ip3u` | Écrit `log.json` dans le dossier Drive du job (créé la première fois, puis mis à jour ; son id est dans `jobs.drive_log_file_id`) : entrées, texte et historique de l'échange, références et mannequin, versions de prompt, toutes les tentatives d'image avec leur brief exact, verdicts, feedback, coûts. Appelé quand la galerie est prête et à la note finale. |

`GET /job-status` renvoie aussi `feedback` (dernier avis explicite par cible, avec raisons et commentaire). Vocabulaire initial des raisons de 👎 : description (`faits_faux`, `ton_inadapte`, `trop_court`, `trop_long`, `info_manquante`, `autre`), plan (`couleur_fausse`, `vetement_deforme`, `texte_ou_imprime_modifie`, `ambiance_ratee`, `rendu_irrealiste`, `autre`), global (`qualite_photos`, `qualite_texte`, `ambiance_ratee`, `trop_cher`, `autre`).

Test réel sur `mufe74xl35gs` : 👍 description, puis changement d'avis en 👎 « trop court » (remplacé, pas dupliqué) ; 👎 sur `porte_miroir` avec raison et commentaire ; raison inconnue → 400 ; job inconnu → 404 ; « garder » décoché sur `porte_miroir` ; note finale 👍 avec commentaire → statut `termine` ; `log.json` créé dans le dossier du job (17 Ko).

Limite : si les 4 plans finissent au même instant, deux `log.json` pourraient être créés la première fois (risque faible, sans conséquence sur les données).

## Étape 6 — Front HTML et endpoints associés (2026-09-24)

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

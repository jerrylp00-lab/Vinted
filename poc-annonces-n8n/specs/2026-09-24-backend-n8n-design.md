# Spec — Back-end n8n de génération de fiches Vinted (PoC-3)

Date : 2026-09-24. Statut : issu d'une session de grilling, validé point par point par l'utilisateur.
Projet indépendant de `poc-annonces/` (Python, conservé intact comme référence). Vocabulaire métier (Fiche, Bibliothèque, Mood, decor_refs, Plan, Brief, Fidélité, Galerie, Mannequin maison) : voir `poc-annonces/CONTEXT.md`, inchangé.

## Problem Statement

Le PoC-2 V2 fonctionne mais repose sur des scripts Python qu'il faut maintenir, sur un fichier statique `decor_index.json`, et sur un état éphémère de session Streamlit. Concrètement :

- La bibliothèque est peu exploitable : pas de choix de la partie utilisée, pas de moods éditables, ajout de photos laborieux (travail manuel sur Drive).
- Rien n'est mémorisé d'une fiche à l'autre : pas de trace des inputs/outputs, pas de feedback, donc aucun moyen d'apprendre des ratés ni d'ajuster les prompts sur des données réelles.
- Le workflow n'est pas automatisable ni déployable simplement : il vit dans des scripts locaux.

## Solution

Refondre tout le back-end en workflows **n8n** (sur le VPS, Docker), sans aucun script Python : n8n est l'orchestrateur à 100 %, avec ses nodes natifs (Webhook, HTTP Request, Code JS, Edit Image, Google Drive, Data Table, Telegram, OpenRouter). Un front HTML unique et volontairement basique appelle des webhooks ; le vrai design viendra dans un second temps sans toucher au back.

Trois apports par rapport au PoC-2 :

1. **Bibliothèque pilotable** : métadonnées en Data Table (moods éditables, actif/inactif), fichiers sur Drive, indexation LLM automatique à l'ajout, sélection de moods autorisés à chaque fiche.
2. **Mémoire** : chaque fiche est journalisée (Data Tables + dossier Drive avec tous les inputs/outputs), notée par l'utilisateur (👍/👎, raisons, commentaire), et un profil de préférences par utilisateur enrichit la génération de texte.
3. **Prompts pilotables** : briefs et prompts versionnés en Data Table, lus à l'exécution ; un workflow manuel séparé propose de nouvelles versions à partir des feedbacks.

## User Stories

Fiche
1. En tant que vendeur, je veux déposer 1 à N photos brutes d'un vêtement, afin d'obtenir une fiche sans saisie manuelle.
2. En tant que vendeur, je veux choisir mon nom (moi / associé) dans le front, afin que mes préférences et mon historique soient les miens.
3. En tant que vendeur, je veux cocher les moods autorisés pour cette fiche (tous cochés par défaut), afin de contrôler quelle partie de la bibliothèque inspire les photos.
4. En tant que vendeur, je veux voir titre, description, mood proposé et decor_refs choisies avant toute génération d'image, afin d'approuver ou corriger avant de dépenser.
5. En tant que vendeur, je veux corriger le mood ou remplacer une decor_ref à la validation, afin de guider le résultat.
6. En tant que vendeur, je veux voir la galerie des 4 plans avec avertissements de fidélité et coût cumulé, afin de décider quoi garder.
7. En tant que vendeur, je veux régénérer un plan seul avec une consigne libre, afin de ne pas repayer les 4.
8. En tant que vendeur, je veux être arrêté et prévenu si une fiche dépasse 1 $, afin de maîtriser le budget.
9. En tant que vendeur, je veux que la génération continue si un plan échoue, afin de ne pas tout perdre.

Feedback
10. En tant que vendeur, je veux mettre 👍/👎 sur la description et sur chaque photo, afin de signaler ce qui marche.
11. En tant que vendeur, je veux qu'un 👎 propose des raisons en un clic (couleur fausse, vêtement déformé, ambiance ratée, autre + texte libre facultatif), afin de qualifier vite.
12. En tant que vendeur, je veux une note finale 👍/👎 avec commentaire libre, afin de résumer la fiche.
13. En tant que responsable des prompts, je veux que chaque régénération soit loggée comme signal négatif implicite, afin d'exploiter des données sans effort.

Bibliothèque
14. En tant qu'utilisateur, je veux voir la bibliothèque en grille avec moods et statut actif/inactif, afin de la relire.
15. En tant qu'utilisateur, je veux corriger les moods d'une photo, afin de rectifier la classification LLM.
16. En tant qu'utilisateur, je veux désactiver une photo sans la supprimer, afin de l'exclure du tirage.
17. En tant qu'utilisateur, je veux uploader de nouvelles inspirations depuis le front, afin qu'elles soient indexées automatiquement (genre, type, moods proposés, description).
18. En tant qu'utilisateur, je veux pouvoir aussi déposer des photos directement dans un dossier Drive « inbox », afin d'être indexées sans passer par le front.
19. En tant qu'utilisateur, je veux une classification LLM initiale de toute la bibliothèque existante en une passe, afin de ne pas tout tagger à la main.

Mémoire et prompts
20. En tant qu'utilisateur, je veux qu'un dossier Drive `Fiches/AAAA-MM-JJ_<job_id>/` contienne inputs, outputs et `log.json`, afin de tout retrouver.
21. En tant qu'utilisateur, je veux que la génération de texte utilise mon profil de préférences (~300 tokens) et 2 fiches passées bien notées (texte seul), afin que le style s'améliore sans surcoût majeur.
22. En tant qu'utilisateur, je veux éditer mon profil `preferences_md` moi-même, afin de garder la main.
23. En tant que responsable des prompts, je veux modifier les prompts dans la Data Table `prompts` sans ouvrir un node, afin d'itérer vite.
24. En tant que responsable des prompts, je veux lancer un workflow d'ajustement sur une période et un prompt donnés, qui crée une version **inactive** proposée par un LLM, afin de valider le diff avant activation.
25. En tant que responsable des prompts, je veux qu'un job enregistre la version de prompt utilisée, afin de relier un résultat à un prompt et de revenir en arrière.

Exploitation
26. En tant qu'opérateur, je veux que les webhooks exigent un secret en header, afin qu'un inconnu ne déclenche pas de dépenses.
27. En tant qu'opérateur, je veux garder le repli Fal → OpenRouter, afin de survivre à l'épuisement du crédit Fal.
28. En tant qu'opérateur, je veux l'export JSON de chaque workflow dans git, afin de restaurer ou redéployer.

## Implementation Decisions

### Architecture générale
- **Nouveau projet** `poc-annonces-n8n/` ; l'ancien `poc-annonces/` reste intact et sert de référence de comportement.
- Instance n8n existante : `https://178-105-102-54.sslip.io` (HTTPS valide, joignable sans VPN, vérifié). Credentials déjà présents : Google Drive OAuth2, Notion, FAL AI (Header Auth), Telegram, OpenRouter. Deux workflows de test existent (« Test Fal — image », « Test Drive — bibliothèque ») et servent d'exemples d'appel Fal et Drive. Aucune Data Table n'existe encore.
- **Aucun Python.** Les Code nodes JS sont autorisés pour l'assemblage de prompts et le parsing. Redimensionnement d'images via le node natif Edit Image ; si un cas s'avère impossible, repli documenté avant de toucher à l'architecture.
- **Asynchrone sans Wait node.** Chaque étape est un workflow court, son état est écrit dans la Data Table `jobs` (statut) ; le front interroge `GET /job/:id` (polling ~3 s). La validation humaine est un webhook séparé.
- **Front** : un fichier HTML unique (3 pages : Nouvelle fiche / Galerie / Bibliothèque), appelle les webhooks. Sélecteur d'utilisateur (moi / associé) sans authentification réelle (auth et rôles plus tard). Volontairement non stylé.
- **Sécurité minimale** : credential Header Auth n8n sur chaque webhook (secret partagé), et « Allowed Origins » (CORS) configuré sur chaque node Webhook (le front local envoie `Origin: null` ou `file://`). Un secret dans un HTML local n'est pas une vraie sécurité : acceptable pour deux personnes de confiance en PoC.

### Data Tables
- `library` : `drive_file_id`, `genre`, `type_vetement`, `moods` (liste), `tags` (libres), `description`, `actif`, `source` (upload / inbox / import initial), `created_at`.
- `users` : `nom`, `preferences_md`, `updated_at`.
- `jobs` : `id`, `user`, `statut`, `mood`, `moods_autorises`, `decor_refs` (ids library), `prompt_versions` (par prompt utilisé), `titre`, `description`, `cout_total`, `drive_folder_id`, `created_at`, `updated_at`, `erreur`.
- `shots` : `job_id`, `plan` (`porte_miroir` / `a_plat` / `cintre` / `detail`), `tentative`, `drive_file_id`, `verdict_fidelite` (`ok`, `problemes[]`), `cout`, `fournisseur` (fal / openrouter), `garde`.
- `feedback` : `job_id`, `cible` (`description` / `plan:<nom>` / `global`), `note` (👍/👎), `raisons[]`, `commentaire`, `implicite` (booléen, vrai pour une régénération), `created_at`.
- `prompts` : `nom`, `version`, `texte`, `actif`, `notes`, `created_at`. Les briefs des 4 plans, le prompt de texte, le prompt d'indexation, le prompt de check de fidélité y vivent. Modifiables dans l'onglet Data Tables de n8n. Un seul `actif` par `nom`.

### Drive
- Bibliothèque : arborescence existante conservée pour les fichiers ; les métadonnées vivent dans `library`. Nouveau dossier `Bibliotheque/_inbox/` surveillé par un trigger.
- Journal : `Fiches/AAAA-MM-JJ_<job_id>/` avec `input/`, `output/` et `log.json` (entrées, brief final envoyé, versions de prompt, verdicts, coûts, feedback).

### Statuts d'un job
`cree` → `texte_en_cours` → `en_attente_validation` → `generation_en_cours` → `galerie_prete` → `termine` ; états d'erreur : `erreur`, `budget_depasse` (attend confirmation).

### Workflows n8n
1. **Indexation bibliothèque** (trigger Drive inbox + webhook d'upload front + mode « import initial » lancé à la main) : vision LLM → genre, type, 1 à 3 moods (liste fermée), description, tags → ligne `library`.
2. **Création de fiche** (webhook `POST /job`) : reçoit photos + user + moods autorisés, crée le job, dossier Drive, lance le texte : LLM vision avec prompt actif + `preferences_md` (~300 tokens max) + 2 few-shot texte seul (même genre × type, notés 👍) → titre, description, mood, questions.
3. **Sélection** : choisit 2-3 `decor_refs` dans `library` (actives, moods autorisés, genre/type compatibles) + mannequin selon le genre ; passe en `en_attente_validation`.
4. **Validation** (`POST /job/:id/valider`, avec éventuelles corrections de mood/refs) : déclenche la génération.
5. **Génération des 4 plans** : un appel image par plan (Fal Nano Banana 2, repli OpenRouter), brief lu dans `prompts`, références assemblées comme dans `poc-annonces/shots.py` ; un plan en échec n'arrête pas les autres ; contrôle de plafond avant chaque appel.
6. **Check de fidélité** : LLM vision compare originaux et image générée → `{ok, problemes[]}` ; 1 retry automatique, puis flag. Une panne du check ne perd pas l'image (comportement du PoC-2).
7. **Régénération d'un plan** (`POST /job/:id/plan/:plan/regenerer`, consigne libre) ; enregistre un feedback implicite.
8. **Feedback** (`POST /job/:id/feedback`).
9. **Lecture** : `GET /job/:id`, `GET /library`, `PATCH /library/:id` (moods, actif), `GET /users/:nom`.
10. **Ajustement de prompts** (lancement manuel, période + nom de prompt) : agrège 👎, raisons, commentaires, régénérations → LLM propose une nouvelle version → ligne `prompts` **inactive**, notification Telegram avec le diff.
11. **Mise à jour du profil user** (lancement manuel) : propose un `preferences_md` révisé, à valider ; jamais d'auto-application.

### Coût et performance
- Plafond par fiche : **1 $** (configurable dans une table/valeur unique) ; dépassement → statut `budget_depasse`, message au front, poursuite seulement sur confirmation. Coût cumulé affiché dans la galerie.
- Profil user injecté **uniquement** dans le prompt de texte, plafonné ~300 tokens ; few-shot : 2 max, texte seul, étape texte seulement.
- Aucun prompt n'est généré dynamiquement par un LLM à l'exécution : le prompt est un template versionné dans lequel le workflow insère des variables.
- Les LLM de fond (profil, digest, ajustement de prompt) utilisent un modèle économique.
- Choix des modèles par étape (texte, vision d'indexation, check de fidélité, digest) : reprendre ceux de `poc-annonces/llm_client.py` par défaut, à confirmer à l'étape 0.

### Contrat webhook (résumé)
Tous les appels portent le header de secret. Réponses JSON. Création : `POST /job` → `{job_id}` puis polling `GET /job/:id` → `{statut, titre, description, mood, decor_refs, shots[], cout_total, erreur}`. Le schéma exact (champs, codes d'erreur) est finalisé à l'étape 3 et consigné dans le README du projet.

## Testing Decisions

- Un bon test ne vérifie que le comportement observable (réponse d'un webhook, ligne écrite en table, fichier créé sur Drive), jamais le détail interne d'un workflow.
- **Seam unique préféré** : le contrat webhook. Chaque étape est validée en l'appelant (`test_workflow`/`execute_workflow` du MCP n8n, ou `curl`) avec des données fixes et en vérifiant les statuts et lignes produits.
- Pin data (`prepare_test_pin_data`) pour isoler les appels payants (Fal, OpenRouter) pendant la mise au point ; un seul test réel de bout en bout par étape image.
- Référence de comportement : rejouer un même jeu de photos que `poc-annonces/Test_humain/` et comparer qualitativement au PoC-2 V2 (évaluation humaine, pas de score automatique).
- Étape 0 vérifie CORS, secret, et création/lecture des Data Tables avant tout workflow métier.

## Out of Scope

- Design du front (UX/UI définitif), historique des fiches dans le front, éditeur de prompts dans le front, digest de feedback automatique/planifié.
- Authentification réelle, rôles, multi-tenant, bibliothèques séparées par utilisateur.
- Publication automatique sur Vinted, gestion des prix.
- Auto-application de modifications de prompts ou de profils.
- Modification ou suppression du Python existant.
- Score de qualité automatique des images au-delà du check de fidélité existant.

## Further Notes

- **Ordre de livraison** (chaque étape testée avant la suivante) : (0) Data Tables, credentials, secret, CORS ; (1) indexation de la bibliothèque + classification initiale ; (2) texte de la fiche ; (3) sélection + validation ; (4) 4 plans + fidélité ; (5) feedback + logs Drive ; (6) front HTML ; (7) workflow d'ajustement de prompts ; (8) profil user + few-shot.
- Les workflows sont construits directement dans n8n via le MCP (lire `get_sdk_reference` et les best practices avant d'écrire), puis exportés en JSON dans `poc-annonces-n8n/workflows/` et versionnés.
- Risques à surveiller : latence cumulée des 4 plans dans n8n (limites de timeout d'exécution), taille des binaires d'images passant par les webhooks, quotas Drive, expiration du crédit Fal (repli OpenRouter à valider en test).
- Décisions non re-litigables héritées du PoC-2 : modèle image natif plutôt que collage, 4 appels séparés, entrées = photos brutes de téléphone, plusieurs références faibles plutôt qu'une seule déterministe.

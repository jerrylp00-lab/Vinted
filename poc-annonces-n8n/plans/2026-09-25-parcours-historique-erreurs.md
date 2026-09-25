# Parcours guidé, historique, erreurs lisibles — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le front compréhensible d'un coup d'œil (3 entrées, parcours Annonce → Inspirations → Photos, journal grisé de l'avancement), ajouter un historique en consultation avec coûts, générer une première photo à valider avant les deux autres, et faire remonter les erreurs de façon lisible.

**Architecture:** Front : un seul `front/index.html` (JS natif), logique pure isolée dans un bloc `// <logic>` testable avec `node --test`. n8n : 3 nouveaux workflows (`Générer la suite`, `Lire les fiches (historique)`, `Erreurs et fiches bloquées`) et de petites modifications de 8 workflows existants, sans refonte. Aucun changement du modèle de données (les statuts sont des chaînes ; un statut nouveau : `premiere_prete`).

**Tech Stack:** n8n (instance `https://178-105-102-54.sslip.io`, outils MCP `mcp__n8n-mcp__*`), Data Tables n8n, Fal.ai + OpenRouter, `front/index.html` (JS natif, sans build), `node --test` (Node ≥ 18) pour la logique pure, navigateur intégré pour les vérifications visuelles, `curl`.

## Décisions arrêtées avec l'utilisateur (2026-09-25)

- Parcours en 3 étapes nommées **Annonce**, **Inspirations**, **Photos de l'annonce**. Navigation : **Créer**, **Historique**, **Réglages**.
- Journal d'avancement grisé, messages réels pour les photos (1/3, 2/3, 3/3) ; pour le texte, un 2ᵉ message temporisé (3 s).
- Anglais masqué : boutons « Modifier la description … » (vêtement, mannequin, chaque inspiration). Pas de mode avancé.
- Inspirations : toute la bibliothèque visible d'emblée ; filtre **multi-moods** (union, aucun = tout) qui sert seulement à afficher ; 1-2 photos **principales** (vision, `decor_refs`), jusqu'à 3 **secondaires** (texte, `inspi_texte`). Le mood envoyé au prompt = union des moods des photos choisies, calculée par le front, sans LLM.
- Plus d'écran « Ce que l'IA va voir ». Génération en deux temps : `porte_miroir` d'abord (~0,08 $), puis « Valider, générer les 2 autres » (~0,16 $) ou « Refaire celle-ci ».
- Feedback : une seule note **globale** à la fin. Le front n'envoie plus que `cible = "global"` ; le workflow de texte accepte le 👍 global pour choisir ses exemples de style.
- Historique : consultation seule, les deux users voient tout, fiches de test incluses, période 7 j / 30 j / tout, coût texte + images. Miniature = 1re photo générée.
- Réglages : Connexion, Profil, Bibliothèque, Prompts, tous éditables (pas de boîte noire).
- Workflow d'erreur global + surveillance des fiches bloquées ; erreurs remontées dans le journal et les écrans.
- Coût Fal : `unités facturées × config_image.fal_cost_per_unit_usd` (formule documentée par Fal). Inchangé.

## Global Constraints

- Plans : exactement `porte_miroir`, `cintre`, `detail`, dans cet ordre.
- Statuts d'un job : `texte_en_cours`, `texte_pret`, `selection_en_cours`, `en_attente_validation`, `generation_en_cours`, **`premiere_prete`** (nouveau), `galerie_prete`, `budget_depasse`, `termine`, `erreur`.
- Préfixes des messages d'erreur dans `jobs.erreur` : `Texte : `, `Style : `, `Photos : ` (le front s'en sert pour savoir à quelle étape afficher l'erreur).
- Interface, titre et description Vinted en français ; prompts, `garment_en`, `mannequin_desc`, `description_en` restent en anglais et ne sont jamais traduits.
- Toute modification de prompt = nouvelle ligne dans `prompts` (aucune n'est prévue ici).
- Secret : header `X-VFN-Secret` sur chaque webhook. Ne jamais écrire le secret dans un fichier, un commit, un log ou une commande copiée dans la conversation ; dans le navigateur, le saisir dans Réglages > Connexion.
- Base des webhooks pour les commandes : `BASE=https://178-105-102-54.sslip.io/webhook/vfn` ; `VFN_SECRET` dans l'environnement du shell (`curl -H "X-VFN-Secret: $VFN_SECRET"`).
- Plafond de coût par fiche inchangé (1 $).
- Ne lancer de génération d'image réelle que dans les tâches qui l'indiquent (Task 16 uniquement) ; ailleurs, `test_workflow` avec données épinglées ou fiches de test sans image.
- Les fiches de test existantes (`mufsg4szpyuj`, `mufsgkl0io7i`, `mufsjqprkf3m`, `muftpawvta7x`…) restent visibles dans l'historique (choix de l'utilisateur).
- Commits : `git add` des fichiers cités uniquement, message se terminant par la ligne `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

## Structure des fichiers

- Modifier : `poc-annonces-n8n/front/index.html` (navigation, parcours, journal, filtre de moods, historique, réglages ; bloc `// <logic>` pur).
- Créer : `poc-annonces-n8n/scripts/test_front_logic.mjs` (tests `node --test` de la logique pure).
- Créer : `poc-annonces-n8n/scripts/check_two_step.sh` (vérifie par `curl` le workflow de génération en deux temps, sans image payante).
- Modifier : `poc-annonces-n8n/README.md` (fin de chaque lot).
- n8n, à modifier (IDs) : `9Y0O9Z4MO9wVM0xB` (générer les plans), `HKMVyeJJQTSoBN6X` (générer un plan), `MIeRXvNz9a4cwKIo` (régénérer), `z1SY3ZkptHVSd4al` (valider), `pGvWMH08Go4yGJYp` (tentative image), `gdGJLLnGtW79Jeol` (texte), `bRdAbgJiiGKwNyvP` (affiner), `kNGZI3ZZSRlckkgP` (modifier une photo de la bibliothèque).
- n8n, à créer : `VFN — Générer la suite (webhook)`, `VFN — Lire les fiches (historique)`, `VFN — Erreurs et fiches bloquées`.

Méthode pour toute édition de workflow n8n : `get_sdk_reference` et `get_workflow_best_practices`, `get_workflow_details` du workflow visé, modification ciblée avec `update_workflow` (les nœuds non cités restent tels quels), `validate_workflow`, puis `publish_workflow` si le workflow est actif, puis le test indiqué. Ne jamais réécrire un workflow de zéro.

---

# LOT 1 — n8n

### Task 1: Sauvegarde préalable

**Files:** aucun.

- [ ] **Step 1: Sauvegarder l'état actuel**

Dans l'UI n8n (`https://178-105-102-54.sslip.io`), ouvrir `VFN — Sauvegarde (manuelle)` et cliquer « Execute workflow ». Attendu : exécution en succès (~80 s), un dossier daté `VFN Sauvegardes/<date>` dans Drive contient 6 tables et les workflows `VFN…` actifs. Demander à l'utilisateur de le faire si l'accès à l'UI n'est pas possible depuis la session.

- [ ] **Step 2: Noter le dossier de sauvegarde dans le README (section Étape 9, dernière ligne)**

Ajouter : `- Sauvegarde avant le lot « parcours / historique / erreurs » : dossier Drive <nom du dossier daté>.`

- [ ] **Step 3: Commit**

```bash
git add poc-annonces-n8n/README.md
git commit -m "docs(poc-annonces-n8n): sauvegarde avant le lot parcours/historique/erreurs

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Génération partielle et statut `premiere_prete` (workflows 8, 9, 11)

**Files:**
- Modify (n8n): `9Y0O9Z4MO9wVM0xB` (renommer en `VFN — Générer les plans (sous-workflow)`), `HKMVyeJJQTSoBN6X`, `MIeRXvNz9a4cwKIo`

**Interfaces:**
- Produces : le sous-workflow `9Y0O9Z4MO9wVM0xB` accepte l'entrée `plans` (chaîne, ex. `"porte_miroir"` ou `"cintre,detail"` ; vide = les 3). Après génération de `porte_miroir` seul, `HKMVyeJJQTSoBN6X` met le job en `premiere_prete`. `POST /job/plan` accepte `premiere_prete` (uniquement pour `porte_miroir`).

- [ ] **Step 1: Écrire le script de vérification (échoue d'abord)**

Créer `poc-annonces-n8n/scripts/check_two_step.sh` :

```bash
#!/usr/bin/env bash
# Vérifie, sans image payante, que le statut premiere_prete et l'endpoint /job/suite existent.
# Usage : VFN_SECRET=... ./scripts/check_two_step.sh <job_id_de_test_en_premiere_prete>
set -euo pipefail
BASE="${BASE:-https://178-105-102-54.sslip.io/webhook/vfn}"
JOB="${1:?job_id manquant}"
H=(-H "X-VFN-Secret: ${VFN_SECRET:?VFN_SECRET manquant}" -H "Content-Type: application/json")
echo "== statut du job"; curl -s "${H[@]}" "$BASE/job-status?id=$JOB" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["statut"], [ (p["plan"],p["statut"]) for p in d["plans"] ])'
echo "== /job/suite sur un job inexistant (attendu 409)"; curl -s -o /dev/null -w "%{http_code}\n" -X POST "${H[@]}" -d '{"job_id":"inexistant"}' "$BASE/job/suite"
echo "== /job/plan cintre quand premiere_prete (attendu 409)"; curl -s -o /dev/null -w "%{http_code}\n" -X POST "${H[@]}" -d "{\"job_id\":\"$JOB\",\"plan\":\"cintre\"}" "$BASE/job/plan"
```

```bash
chmod +x poc-annonces-n8n/scripts/check_two_step.sh
```

- [ ] **Step 2: Modifier `9Y0O9Z4MO9wVM0xB`**

(a) Renommer en `VFN — Générer les plans (sous-workflow)`, description : `Crée (une fois) le dossier output du job et lance les plans demandés en parallèle (entrée plans : liste séparée par des virgules, vide = les 3).`

(b) Trigger `Appelé par un workflow` : ajouter l'entrée `plans` de type `string` (après `job_id`).

(c) Après `Lire le job`, insérer un nœud If `Dossier output déjà créé ?` : condition `{{ $json.drive_output_folder_id }}` notEmpty (string, strict). Branche vraie → Code `Réutiliser le dossier output` ; branche fausse → `Créer le dossier output` (nœud Drive existant). Les deux vont vers `Passer le job en génération`.

Code `Réutiliser le dossier output` (mode `runOnceForAllItems`) :

```js
return [{ json: { id: $('Lire le job').first().json.drive_output_folder_id } }];
```

(d) Le nœud Drive `Créer le dossier output` référence `$json.drive_folder_id` : le remplacer par `{{ $('Lire le job').first().json.drive_folder_id }}`. Le nœud `Passer le job en génération` utilise déjà `{{ $json.id }}` pour `drive_output_folder_id` : inchangé.

(e) Code du nœud `Les 3 plans` (renommer `Les plans demandés`) :

```js
const job_id = $('Lire le job').first().json.job_id;
const asked = String($('Appelé par un workflow').first().json.plans || '').split(',').map(s => s.trim()).filter(Boolean);
const all = ['porte_miroir', 'cintre', 'detail'];
const plans = asked.length ? all.filter(p => asked.includes(p)) : all;
return plans.map(plan => ({ json: { job_id, plan, feedback: '', force: '' } }));
```

- [ ] **Step 3: Modifier `HKMVyeJJQTSoBN6X` (statut après un plan)**

Remplacer le code du nœud `Décider le statut du job` par :

```js
const job_id = $('Appelé par un workflow').first().json.job_id;
const shots = $input.all().map(i => i.json).filter(s => s.job_id);
const cur = p => shots.find(s => s.plan === p && s.courant === true);
const isBudget = s => String((s && s.erreur) || '').startsWith('Plafond');
const [pm, ci, de] = ['porte_miroir', 'cintre', 'detail'].map(cur);
if (pm && ci && de) return [{ json: { job_id, statut: [pm, ci, de].some(isBudget) ? 'budget_depasse' : 'galerie_prete' } }];
const autresPlans = shots.some(s => s.plan !== 'porte_miroir');
if (pm && !autresPlans) return [{ json: { job_id, statut: isBudget(pm) ? 'budget_depasse' : 'premiere_prete' } }];
return [{ json: { job_id, statut: '' } }];
```

Le reste du workflow (If `notEmpty`, mise à jour du statut, journal) est inchangé. Mettre à jour la description : `Génère un plan (une seule tentative) puis met le job en premiere_prete (1 plan) ou galerie_prete (3 plans).`

- [ ] **Step 4: Modifier `MIeRXvNz9a4cwKIo` (régénérer)**

Dans le nœud If `Régénération possible ?`, remplacer l'expression par :

```
{{ (() => { const b = $('Webhook régénérer un plan').first().json.body || {}; const st = $json.statut; const okPlan = ['porte_miroir', 'cintre', 'detail'].includes(b.plan); if (!$json.job_id || !okPlan) return false; if (st === 'premiere_prete') return b.plan === 'porte_miroir'; return ['galerie_prete', 'budget_depasse'].includes(st); })() }}
```

Dans le nœud `Passer le job en génération`, ajouter la colonne `erreur` = chaîne vide (en plus de `statut`) pour effacer un ancien message. Le corps du 409 reste inchangé.

- [ ] **Step 5: Valider et publier les 3 workflows**

`validate_workflow` sur chacun (aucune erreur), puis `publish_workflow` sur `9Y0O9Z4MO9wVM0xB`, `HKMVyeJJQTSoBN6X`, `MIeRXvNz9a4cwKIo`.

- [ ] **Step 6: Vérifier le sous-workflow 8 avec données épinglées**

`test_workflow` sur `9Y0O9Z4MO9wVM0xB` avec un `job_id` de fiche de test qui a déjà un `drive_output_folder_id` (ex. `muftpawvta7x`) et `plans = "porte_miroir"` en **épinglant** le nœud `Lancer le plan` (aucun appel Fal). Attendu : le nœud `Les plans demandés` sort exactement 1 item (`porte_miroir`) et le nœud `Créer le dossier output` n'est pas exécuté.

Expected : sortie de `Les plans demandés` = `[{job_id:"muftpawvta7x", plan:"porte_miroir", …}]`.

- [ ] **Step 7: Vérifier qu'une fiche déjà terminée n'est pas affectée (aucun coût)**

```bash
curl -s -H "X-VFN-Secret: $VFN_SECRET" "https://178-105-102-54.sslip.io/webhook/vfn/job-status?id=muftpawvta7x" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["statut"], [(p["plan"],p["statut"]) for p in d["plans"]])'
```

Expected : `galerie_prete [('porte_miroir','pret'), ('cintre','pret'), ('detail','pret')]`. Ne **pas** lancer `check_two_step.sh` sur cette fiche : sa 3ᵉ commande (`/job/plan` sur `cintre`) serait acceptée et déclencherait une génération payante. Le script est prévu pour une fiche en `premiere_prete` (Task 16, Step 3).

- [ ] **Step 8: Commit**

```bash
git add poc-annonces-n8n/scripts/check_two_step.sh
git commit -m "feat(poc-annonces-n8n): generation partielle des plans et statut premiere_prete

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `plans` dans `Valider` et endpoint `POST /job/suite`

**Files:**
- Modify (n8n): `z1SY3ZkptHVSd4al`
- Create (n8n): `VFN — Générer la suite (webhook)`

**Interfaces:**
- Consumes : entrée `plans` du sous-workflow `9Y0O9Z4MO9wVM0xB` (Task 2).
- Produces : `POST /job/valider` accepte `plans: ["porte_miroir"]` (liste facultative ; absent = les 3). `POST /job/suite` `{job_id}` → 200 `{job_id, statut:"generation_en_cours"}` ; 409 `{error, statut}` si le job n'est pas `premiere_prete` ou si la première photo est en erreur.

- [ ] **Step 1: Écrire le test qui échoue**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "X-VFN-Secret: $VFN_SECRET" -H "Content-Type: application/json" -d '{"job_id":"inexistant"}' https://178-105-102-54.sslip.io/webhook/vfn/job/suite
```

Expected : `404` (le webhook n'existe pas encore).

- [ ] **Step 2: Modifier `z1SY3ZkptHVSd4al`**

Dans le Code `Appliquer les corrections`, avant la ligne `const mood = …`, ajouter :

```js
const ALL_PLANS = ['porte_miroir', 'cintre', 'detail'];
let plansAsk = [];
if (body.plans !== undefined) {
  if (!Array.isArray(body.plans) || body.plans.some(p => !ALL_PLANS.includes(p))) return fail('plans doit être une liste parmi porte_miroir, cintre, detail');
  plansAsk = ALL_PLANS.filter(p => body.plans.includes(p));
}
```

Et dans l'objet retourné `json: { … }`, ajouter la clé `plans_csv: plansAsk.join(',')`. Dans le nœud Execute Workflow `Lancer la génération` (workflow `9Y0O9Z4MO9wVM0xB`), ajouter l'entrée `plans` avec l'expression `{{ $('Appliquer les corrections').first().json.plans_csv }}` (ajouter `plans` au schéma d'entrée du nœud). La réponse 400 existante (`Répondre 400`) renvoie déjà `{error}`.

- [ ] **Step 3: Créer `VFN — Générer la suite (webhook)`**

Nœuds (tous les nœuds Data Table utilisent les mêmes tables que les autres workflows : `jobs` `vVa4oB747ymKwzw8`, `shots` `qssjFRjdNaiMzoNG`) :

1. `Webhook générer la suite` : POST, chemin `vfn/job/suite`, auth Header Auth (credential `VFN webhook secret`), `responseMode: responseNode`, `allowedOrigins: *`.
2. `Lire le job` : Data Table `get` sur `jobs`, filtre `job_id eq {{ $json.body.job_id }}`, `returnAll`, `alwaysOutputData: true`.
3. `Lire les shots` : Data Table `get` sur `shots`, filtre `job_id eq {{ $('Lire le job').first().json.job_id || 'aucun' }}`, `returnAll`, `alwaysOutputData: true`, `executeOnce: true`.
4. `Vérifier` (Code, `runOnceForAllItems`) :

```js
const job = $('Lire le job').first().json;
const shots = $('Lire les shots').all().map(i => i.json).filter(s => s.job_id);
if (!job.job_id) return [{ json: { ok: false, statut: null, error: 'job introuvable' } }];
if (job.statut !== 'premiere_prete') return [{ json: { ok: false, statut: job.statut, error: 'la première photo n\'est pas prête à être validée' } }];
const pm = shots.find(s => s.plan === 'porte_miroir' && s.courant === true);
if (!pm || pm.erreur || !pm.drive_file_id) return [{ json: { ok: false, statut: job.statut, error: 'la première photo est en échec : refais-la avant de continuer' } }];
return [{ json: { ok: true, job_id: job.job_id } }];
```

5. `Peut continuer ?` : If `{{ $json.ok }}` true.
6. `Passer en génération` : Data Table `update` sur `jobs`, filtre `job_id eq {{ $json.job_id }}`, colonnes `statut = generation_en_cours`, `erreur = ""`.
7. `Répondre ok` : Respond to Webhook JSON `{{ { "job_id": $('Vérifier').first().json.job_id, "statut": "generation_en_cours" } }}`.
8. `Lancer les 2 autres plans` : Execute Workflow `9Y0O9Z4MO9wVM0xB`, mode `once`, `waitForSubWorkflow: false`, entrées `job_id = {{ $('Vérifier').first().json.job_id }}`, `plans = cintre,detail`.
9. `Répondre 409` (branche fausse du If) : Respond JSON `{{ { "error": $json.error, "statut": $json.statut } }}`, code 409.

Connexions : 1→2→3→4→5 ; 5 vrai→6→7→8 ; 5 faux→9.

Description : `Webhook POST /vfn/job/suite : après validation de la première photo (premiere_prete), lance cintre et detail.`

- [ ] **Step 4: Valider et publier**

`validate_workflow` puis `publish_workflow` sur `z1SY3ZkptHVSd4al` et sur le nouveau workflow.

- [ ] **Step 5: Vérifier**

```bash
# job inexistant : 409
curl -s -w " %{http_code}\n" -X POST -H "X-VFN-Secret: $VFN_SECRET" -H "Content-Type: application/json" -d '{"job_id":"inexistant"}' https://178-105-102-54.sslip.io/webhook/vfn/job/suite
# job déjà en galerie_prete : 409 (aucune génération lancée)
curl -s -w " %{http_code}\n" -X POST -H "X-VFN-Secret: $VFN_SECRET" -H "Content-Type: application/json" -d '{"job_id":"muftpawvta7x"}' https://178-105-102-54.sslip.io/webhook/vfn/job/suite
# valider avec un plan invalide : 400 (job de test en attente de validation requis ; sinon 409 est aussi accepté)
curl -s -w " %{http_code}\n" -X POST -H "X-VFN-Secret: $VFN_SECRET" -H "Content-Type: application/json" -d '{"job_id":"muftpawvta7x","plans":["truc"]}' https://178-105-102-54.sslip.io/webhook/vfn/job/valider
# sans secret : 403
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://178-105-102-54.sslip.io/webhook/vfn/job/suite
```

Expected : `{"error":"job introuvable","statut":null} 409`, `{"error":"la première photo n'est pas prête…","statut":"galerie_prete"} 409`, `409` (le job n'est pas en attente de validation, le contrôle de `plans` n'est atteint que sur un job `en_attente_validation` : le 400 est vérifié en Task 16), `403`.

- [ ] **Step 6: Commit**

```bash
git add poc-annonces-n8n/scripts/check_two_step.sh
git commit -m "feat(poc-annonces-n8n): parametre plans sur /job/valider et endpoint /job/suite

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Petits ajustements (mood vide, 👍 global, retry du texte, description en bibliothèque)

**Files:**
- Modify (n8n): `pGvWMH08Go4yGJYp`, `gdGJLLnGtW79Jeol`, `bRdAbgJiiGKwNyvP`, `kNGZI3ZZSRlckkgP`

- [ ] **Step 1: Tentative image — ne pas écrire « Overall mood: . »**

Dans le Code `Assembler la requête image` de `pGvWMH08Go4yGJYp`, remplacer la ligne :

```js
parts.push('Overall mood: ' + ctx.mood + '.');
```

par :

```js
if (String(ctx.mood || '').trim()) parts.push('Overall mood: ' + String(ctx.mood).trim() + '.');
```

- [ ] **Step 2: Texte — accepter le 👍 global pour les exemples de style**

Dans le Code `Construire la requête texte` de `gdGJLLnGtW79Jeol`, remplacer :

```js
.filter(f => f.job_id && !f.implicite && f.cible === 'description' && f.note === '👍')
```

par :

```js
.filter(f => f.job_id && !f.implicite && (f.cible === 'description' || f.cible === 'global') && f.note === '👍')
```

- [ ] **Step 3: Affiner le texte — relance sans message (`retry`)**

Dans le Code `Ajouter le message à l'historique` de `bRdAbgJiiGKwNyvP`, remplacer les 5 lignes après `const job = …` par :

```js
const body = $('Webhook affiner le texte').first().json.body || {};
const message = String(body.message || '').trim();
const retry = body.retry === true;
if (!message && !retry) throw new Error('Champ message manquant');
if (job.statut === 'texte_en_cours') throw new Error('Une génération de texte est déjà en cours pour ce job');
let history = [];
try { history = JSON.parse(job.historique || '[]'); } catch (e) {}
if (message) history.push({ role: 'user', content: message });
return [{ json: { job_id: job.job_id, historique: JSON.stringify(history) } }];
```

(Le nœud garde sa première ligne `const job = $input.first().json;`.)

- [ ] **Step 4: Bibliothèque — `description_en` modifiable**

Dans le Code `Valider la modification` de `kNGZI3ZZSRlckkgP`, avant `return [{ json: { ok: true, … } }]`, ajouter :

```js
let description_en = row.description_en || '';
if (body.description_en !== undefined) {
  if (typeof body.description_en !== 'string') return fail(400, 'description_en doit être un texte');
  description_en = body.description_en.trim();
  if (description_en.length > 2000) return fail(400, 'description_en trop longue (2000 caractères maximum)');
}
```

et remplacer le `return` final par :

```js
return [{ json: { ok: true, drive_file_id: row.drive_file_id, moods: JSON.stringify(moods), tags: JSON.stringify(tags), actif, description_en } }];
```

Dans `Enregistrer la modification`, ajouter la colonne `description_en = {{ $json.description_en }}` (avec `moods`, `tags`, `actif`), et dans `Répondre ok` ajouter `"description_en": $('Valider la modification').first().json.description_en` à l'objet renvoyé.

- [ ] **Step 5: Valider, publier, vérifier**

`validate_workflow` puis `publish_workflow` sur les 4. Vérifier :

```bash
# description_en accepte un texte (photo de test inactive du README), puis la remettre à l'identique
curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H "Content-Type: application/json" -d '{"drive_file_id":"1AAsnk4COM1pf6iXF-kWEr8ay1x9PLVVz","description_en":"test"}' https://178-105-102-54.sslip.io/webhook/vfn/library/update
# type invalide : 400
curl -s -w " %{http_code}\n" -X POST -H "X-VFN-Secret: $VFN_SECRET" -H "Content-Type: application/json" -d '{"drive_file_id":"1AAsnk4COM1pf6iXF-kWEr8ay1x9PLVVz","description_en":123}' https://178-105-102-54.sslip.io/webhook/vfn/library/update
# texte sans message ni retry : la génération ne démarre pas (erreur côté workflow, pas de 200 {"statut":"texte_en_cours"})
```

Expected : première réponse `{"ok":true,…,"description_en":"test"}` ; deuxième `{"error":"description_en doit être un texte"} 400`. Avant le premier appel, noter la `description_en` actuelle de cette photo (`GET /library`, champ `description_en`), puis la remettre avec un troisième appel `POST /library/update` à la fin du test.

- [ ] **Step 6: Pas de commit ici**

Aucun fichier du dépôt n'est modifié dans cette tâche ; le README est mis à jour en Task 7.

---

### Task 5: `GET /jobs` (historique)

**Files:**
- Create (n8n): `VFN — Lire les fiches (historique)`

**Interfaces:**
- Produces : `GET /jobs` → `{ jobs: [{ job_id, user, titre, statut, genre, type_vetement, created_at, cout_texte, cout_images, cout_total, nb_images, nb_regenerations, cover_file_id, note_globale }] }` trié par `created_at` décroissant. `cover_file_id` = image courante de `porte_miroir`, sinon toute image courante, sinon `""`. `note_globale` = `"👍"`, `"👎"` ou `""`.

- [ ] **Step 1: Écrire le test qui échoue**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "X-VFN-Secret: $VFN_SECRET" https://178-105-102-54.sslip.io/webhook/vfn/jobs
```

Expected : `404`.

- [ ] **Step 2: Créer le workflow**

Nœuds : `Webhook liste des fiches` (GET, chemin `vfn/jobs`, Header Auth, `responseNode`, `allowedOrigins *`) → `Lire les jobs` (Data Table get `jobs`, `returnAll`, `alwaysOutputData`, `executeOnce`) → `Lire les shots` (get `shots`, idem) → `Lire le feedback` (get `feedback`, idem) → `Mettre en forme` (Code) → `Répondre` (Respond JSON `{{ $json }}`).

Code `Mettre en forme` (`runOnceForAllItems`) :

```js
const jobs = $('Lire les jobs').all().map(i => i.json).filter(j => j.job_id);
const shots = $('Lire les shots').all().map(i => i.json).filter(s => s.job_id);
const fbs = $('Lire le feedback').all().map(i => i.json).filter(f => f.job_id && f.cible === 'global' && !f.implicite);
const out = jobs.map(j => {
  const sh = shots.filter(s => s.job_id === j.job_id);
  const imgs = sh.filter(s => s.drive_file_id);
  const plansAvecImage = new Set(imgs.map(s => s.plan));
  const cover = sh.find(s => s.plan === 'porte_miroir' && s.courant === true && s.drive_file_id) || sh.find(s => s.courant === true && s.drive_file_id);
  const fb = fbs.find(f => f.job_id === j.job_id);
  const cout_images = sh.reduce((a, s) => a + Number(s.cout || 0), 0);
  const cout_texte = Number(j.cout_total || 0);
  return {
    job_id: j.job_id, user: j.user, titre: j.titre || '', statut: j.statut, genre: j.genre, type_vetement: j.type_vetement,
    created_at: j.createdAt, cout_texte, cout_images, cout_total: cout_texte + cout_images,
    nb_images: imgs.length, nb_regenerations: Math.max(0, imgs.length - plansAvecImage.size),
    cover_file_id: cover ? cover.drive_file_id : '', note_globale: fb ? fb.note : ''
  };
}).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
return [{ json: { jobs: out } }];
```

Description : `Webhook GET /vfn/jobs : liste des fiches (toutes, tous users) avec coûts et nombre d'images, pour l'historique.`

- [ ] **Step 3: Valider, publier, vérifier**

```bash
curl -s -H "X-VFN-Secret: $VFN_SECRET" https://178-105-102-54.sslip.io/webhook/vfn/jobs | python3 -c 'import sys,json; d=json.load(sys.stdin)["jobs"]; print(len(d), "fiches"); print(d[0]); print("somme coûts:", round(sum(j["cout_total"] for j in d),4))'
curl -s -o /dev/null -w "%{http_code}\n" https://178-105-102-54.sslip.io/webhook/vfn/jobs
```

Expected : nombre de fiches égal au nombre de lignes de la table `jobs`, première fiche = la plus récente (`created_at` décroissant), `cout_total` de `muftpawvta7x` ≈ 0,24 $ à 0,0002 $ près et `nb_images` ≥ 3, puis `403` sans secret. Comparer `cout_total` d'une fiche avec `cout_total` de `GET /job-status?id=<job>` : identiques.

- [ ] **Step 4: Commit (README à la Task 7)**

Aucun fichier du dépôt modifié dans cette tâche : ne pas committer.

---

### Task 6: Erreurs lisibles et fiches bloquées

**Files:**
- Create (n8n): `VFN — Erreurs et fiches bloquées`
- Modify (n8n, réglage seulement) : `errorWorkflow` sur `5erMviLZ0qLPtd1E`, `gdGJLLnGtW79Jeol`, `bRdAbgJiiGKwNyvP`, `ao81dPakf9IqTIyr`, `FI9HyhPdvbATuSqw`, `z1SY3ZkptHVSd4al`, `9Y0O9Z4MO9wVM0xB`, `HKMVyeJJQTSoBN6X`, `pGvWMH08Go4yGJYp`, `MIeRXvNz9a4cwKIo` et le nouveau `Générer la suite`.

**Interfaces:**
- Produces : plus aucun job ne reste indéfiniment en `texte_en_cours`, `selection_en_cours` ou `generation_en_cours`. Texte/style : `statut = erreur`, `erreur = "Texte : …"` / `"Style : …"` dès l'erreur. Photos : message immédiat dans `jobs.erreur`, puis, après le délai de surveillance, une ligne `shots` en erreur par plan manquant et le bon statut (`premiere_prete` ou `galerie_prete`).

Rappel : le déclencheur d'erreur ne fournit pas les entrées de l'exécution en échec (pas de `job_id`) : on cible donc le job à partir du statut occupé correspondant au workflow qui a échoué, seulement s'il n'y en a qu'un ; sinon la surveillance planifiée tranche.

- [ ] **Step 1: Écrire le test qui échoue**

Créer une fiche de test défectueuse (aucun coût) : insérer avec l'outil `add_data_table_rows` dans `jobs` (`vVa4oB747ymKwzw8`) une ligne `job_id = "test_erreur"`, `user = "Jeremy"`, `statut = "texte_en_cours"`, `genre = "femme"`, `type_vetement = "haut"`, `drive_input_folder_id = "dossier_inexistant"`, `historique = "[]"`, `moods_autorises = "[]"`, `cout_total = 0`, `erreur = ""`, `texte_visible = "false"`, `prompt_versions = "{}"`, `questions = "[]"`. Puis `execute_workflow` (mode production) sur `gdGJLLnGtW79Jeol` avec `job_id = "test_erreur"`.

```bash
curl -s -H "X-VFN-Secret: $VFN_SECRET" "https://178-105-102-54.sslip.io/webhook/vfn/job-status?id=test_erreur" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["statut"], repr(d["erreur"]))'
```

Expected (avant le correctif) : `texte_en_cours ''` : la fiche reste coincée (l'exécution échoue sans que personne ne le dise).

- [ ] **Step 2: Créer le workflow `VFN — Erreurs et fiches bloquées`**

Nœuds :

1. `Erreur d'un workflow` : `n8n-nodes-base.errorTrigger`.
2. `Toutes les 2 minutes` : Schedule Trigger, intervalle 2 minutes.
3. `Lire les jobs` : Data Table `get` sur `jobs`, `returnAll`, `alwaysOutputData`, `executeOnce`. Les deux triggers vont vers ce nœud.
4. `Lire les shots` : Data Table `get` sur `shots`, `returnAll`, `alwaysOutputData`, `executeOnce`.
5. `Décider` : Code, `runOnceForAllItems` :

```js
const now = Date.now();
const jobs = $('Lire les jobs').all().map(i => i.json).filter(j => j.job_id);
const shots = $('Lire les shots').all().map(i => i.json).filter(s => s.job_id);
const fromError = $('Erreur d\'un workflow').isExecuted;
const LIMITES = { texte_en_cours: 4, selection_en_cours: 3, generation_en_cours: 8 };   // minutes
const LIMITE_PHOTOS_AVEC_MESSAGE = 1.5;                                                  // minutes, si une erreur Photos est déjà notée
const ETAPE = { texte_en_cours: 'Texte', selection_en_cours: 'Style', generation_en_cours: 'Photos' };
const ALL = ['porte_miroir', 'cintre', 'detail'];
const out = [];

const ageMin = j => (now - new Date(j.updatedAt).getTime()) / 60000;
const shotsOf = j => shots.filter(s => s.job_id === j.job_id);
const current = (j, p) => shotsOf(j).find(s => s.plan === p && s.courant === true);
const isBudget = s => String((s && s.erreur) || '').startsWith('Plafond');
const statutPhotos = (j, extra) => {
  const cur = p => extra.find(s => s.plan === p) || current(j, p);
  const [pm, ci, de] = ALL.map(cur);
  if (pm && ci && de) return [pm, ci, de].some(isBudget) ? 'budget_depasse' : 'galerie_prete';
  const autres = shotsOf(j).some(s => s.plan !== 'porte_miroir') || extra.some(s => s.plan !== 'porte_miroir');
  if (pm && !autres) return isBudget(pm) ? 'budget_depasse' : 'premiere_prete';
  return 'galerie_prete';
};

if (fromError) {
  const e = $('Erreur d\'un workflow').first().json;
  const wf = String((e.workflow && e.workflow.name) || '').replace(/^VFN — /, '');
  const msg = String((e.execution && e.execution.error && e.execution.error.message) || 'erreur inconnue').slice(0, 300);
  const busy = /texte|Créer une fiche/i.test(wf) ? 'texte_en_cours'
    : /style/i.test(wf) ? 'selection_en_cours'
    : /image|plan|Valider|suite/i.test(wf) ? 'generation_en_cours' : '';
  const cands = busy ? jobs.filter(j => j.statut === busy) : [];
  if (cands.length === 1) {
    const j = cands[0], etape = ETAPE[busy];
    const texte = etape + ' : ' + msg + ' (étape « ' + wf + ' »)';
    if (etape === 'Photos') out.push({ kind: 'job', job_id: j.job_id, erreur: texte });               // statut inchangé : la surveillance tranche
    else out.push({ kind: 'job', job_id: j.job_id, statut: 'erreur', erreur: texte });
  }
} else {
  for (const j of jobs) {
    const etape = ETAPE[j.statut]; if (!etape) continue;
    const limite = etape === 'Photos' && String(j.erreur || '').startsWith('Photos') ? LIMITE_PHOTOS_AVEC_MESSAGE : LIMITES[j.statut];
    if (ageMin(j) <= limite) continue;
    const message = String(j.erreur || '').replace(/^(Texte|Style|Photos) : /, '') || 'Le traitement a été interrompu (délai dépassé).';
    if (etape !== 'Photos') { out.push({ kind: 'job', job_id: j.job_id, statut: 'erreur', erreur: etape + ' : ' + message }); continue; }
    const manquants = !current(j, 'porte_miroir') ? ['porte_miroir'] : ['cintre', 'detail'].filter(p => !current(j, p));
    const extra = manquants.map(plan => ({
      kind: 'shot', job_id: j.job_id, plan, tentative: shotsOf(j).filter(s => s.plan === plan).reduce((m, s) => Math.max(m, Number(s.tentative || 0)), 0) + 1,
      drive_file_id: '', fidelite_ok: false, fidelite_verifiee: false, fidelite_problemes: '[]', cout: 0, fournisseur: '', garde: false, courant: true, erreur: 'Photos : ' + message, brief: ''
    }));
    out.push(...extra);
    out.push({ kind: 'job', job_id: j.job_id, statut: statutPhotos(j, extra), erreur: '' });
  }
}
return out.map(x => ({ json: x }));
```

6. `Type de mise à jour` : Switch sur `{{ $json.kind }}` : sortie `shot` et sortie `job`.
7. `Enregistrer l'échec d'un plan` (sortie `shot`) : Data Table `insert` sur `shots` avec les colonnes `job_id, plan, tentative, drive_file_id, fidelite_ok, fidelite_verifiee, fidelite_problemes, cout, fournisseur, garde, courant, erreur, brief` prises dans `$json` (mêmes noms).
8. `Mettre à jour la fiche` (sortie `job`) : Data Table `update` sur `jobs`, filtre `job_id eq {{ $json.job_id }}`, colonnes `statut = {{ $json.statut || $('Lire les jobs').all().map(i => i.json).find(j => j.job_id === $json.job_id).statut }}`, `erreur = {{ $json.erreur }}`.

Exécuter les nœuds 7 puis 8 dans cet ordre pour un même job (les lignes `shot` sortent avant la ligne `job` dans le Code, et Switch conserve l'ordre) : configurer le workflow avec `executionOrder: v1` et brancher `Type de mise à jour` sortie `shot` → 7 → (fin) et sortie `job` → 8 ; si l'ordre n'est pas garanti à l'exécution, remplacer le Switch par deux Code `Filtrer les plans` / `Filtrer les fiches` qui trient (`shot` d'abord) et enchaîner 7 → 8 avec un nœud Merge « Wait for both ».

Description : `Error Trigger + surveillance toutes les 2 min : passe en erreur (avec un message lisible) les fiches dont une étape a échoué ou dépassé son délai (texte 4 min, style 3 min, photos 8 min ou 1,5 min après un message d'erreur), et complète les plans manquants par une ligne d'échec.`

- [ ] **Step 3: Régler `errorWorkflow` sur chaque workflow de la liste**

Pour chacun des 11 workflows listés en « Files », `update_workflow` avec `settings.errorWorkflow = <id du nouveau workflow>` (les nœuds ne changent pas). Publier le nouveau workflow (`publish_workflow`) pour que le Schedule et l'Error Trigger soient actifs, puis republier ceux qui étaient publiés.

- [ ] **Step 4: Vérifier l'erreur immédiate (texte)**

Relancer le test du Step 1 (même fiche `test_erreur` remise à `texte_en_cours` avec `update` de la ligne si besoin, puis `execute_workflow` sur `gdGJLLnGtW79Jeol`, `job_id = "test_erreur"`). Attendre 10 s.

```bash
curl -s -H "X-VFN-Secret: $VFN_SECRET" "https://178-105-102-54.sslip.io/webhook/vfn/job-status?id=test_erreur" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["statut"], repr(d["erreur"]))'
```

Expected : `erreur 'Texte : … (étape « Générer le texte (sous-workflow) »)'`. Si le statut reste `texte_en_cours` : l'Error Trigger n'a pas été déclenché pour un sous-workflow ; dans ce cas la surveillance (Step 5) est le filet de sécurité : noter la constatation dans le README et poursuivre.

- [ ] **Step 5: Vérifier la surveillance avec données épinglées**

`test_workflow` sur le nouveau workflow avec le déclencheur `Toutes les 2 minutes` et les nœuds `Lire les jobs` / `Lire les shots` épinglés :

- job A `{job_id:"a", statut:"generation_en_cours", updatedAt: <il y a 20 minutes>, erreur:""}` sans aucun shot ;
- job B `{job_id:"b", statut:"generation_en_cours", updatedAt: <il y a 20 minutes>, erreur:""}` avec un shot courant `porte_miroir` (`drive_file_id:"x"`) ;
- job C `{job_id:"c", statut:"texte_en_cours", updatedAt: <il y a 1 minute>}`.

Expected (sortie de `Décider`) : pour A, un item `shot` (`porte_miroir`, `erreur "Photos : Le traitement a été interrompu (délai dépassé)."`) puis un item `job` `statut = premiere_prete`, `erreur ''` ; pour B, deux items `shot` (`cintre`, `detail`) puis `job` `statut = galerie_prete` ; rien pour C.

- [ ] **Step 6: Nettoyer et commit**

Supprimer la ligne `test_erreur` de `jobs` depuis l'UI n8n (Data Tables). Le README est mis à jour en Task 7.

---

### Task 7: README du lot 1

**Files:**
- Modify: `poc-annonces-n8n/README.md`

- [ ] **Step 1: Mettre à jour la section « Référence des workflows n8n »**

- Tableau d'ensemble : renommer le n°8 en `Générer les plans` ; ajouter les 3 lignes `29 Générer la suite (webhook, POST /job/suite)`, `30 Lire les fiches (historique) (webhook, GET /jobs)`, `31 Erreurs et fiches bloquées (Error Trigger + toutes les 2 min)` avec leurs IDs relevés dans n8n ; le total passe à **30 workflows, dont 29 publiés et 1 inactif** (le n°28 étant archivé).
- Fiches des workflows 2 (👍 global), 3 (`retry`), 7 (`plans`), 8, 9 (statut `premiere_prete`), 10 (mood vide), 11 (`premiere_prete` pour `porte_miroir`), 17 (`description_en`) : mettre à jour les descriptions.
- Ajouter les fiches des trois nouveaux workflows (chemin, entrées, sorties, codes d'erreur, messages).
- Ajouter le statut `premiere_prete` dans la « Chaîne d'appels » et dans la liste des statuts.
- Supprimer de la liste « points de robustesse » le point 1 (fiche coincée) et noter le résultat du Step 4 de la Task 6.

- [ ] **Step 2: Commit**

```bash
git add poc-annonces-n8n/README.md
git commit -m "docs(poc-annonces-n8n): lot 1 (generation en deux temps, historique, erreurs)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

# LOT 2 — Front (`poc-annonces-n8n/front/index.html`)

Le front est un fichier unique ; les tâches 8 à 15 le modifient de haut en bas. Les numéros de ligne cités sont ceux du fichier avant la Task 9 ; après chaque tâche, repérer les blocs par leur contenu (ancres), pas par le numéro.

Pour toute vérification visuelle : démarrer un serveur statique et ouvrir la page dans le navigateur intégré.

```bash
python3 -m http.server 8765 -d poc-annonces-n8n/front
```

Ouvrir `http://localhost:8765`. Si Réglages demande le secret, demander à l'utilisateur de le saisir lui-même dans Réglages > Connexion (le navigateur le garde en `localStorage`).

### Task 8: Logique pure et tests (TDD)

**Files:**
- Create: `poc-annonces-n8n/scripts/test_front_logic.mjs`
- Modify: `poc-annonces-n8n/front/index.html` (nouveau bloc `// <logic>` juste après la ligne `"use strict";`)

**Interfaces:**
- Produces (dans le bloc `// <logic>`), utilisés par les tâches 9 à 14 :
  - `PLAN_LABELS`, `PLAN_ORDER`
  - `stepOf(job) → 1|2|3`
  - `moodUnion(items, selectedIds) → string[]` (moods triés par fréquence puis alphabétique)
  - `filterByMoods(items, moods) → items[]` (actifs seulement ; `moods` vide = tous)
  - `cleanErr(msg) → string` (retire un préfixe `Texte : `, `Style : `, `Photos : `)
  - `journalLines(prev, cur) → [{text, kind}]` (`kind` : `info`, `ok`, `err`)
  - `summarize(jobs, days, now) → {fiches, images, regenerations, cout_texte, cout_images, cout_total, list}`

- [ ] **Step 1: Écrire le test qui échoue**

Créer `poc-annonces-n8n/scripts/test_front_logic.mjs` :

```js
import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../front/index.html", import.meta.url), "utf8");
const m = html.match(/\/\/ <logic>([\s\S]*?)\/\/ <\/logic>/);
assert.ok(m, "bloc // <logic> introuvable dans front/index.html");
const L = new Function(m[1] + "\nreturn { PLAN_LABELS, PLAN_ORDER, stepOf, moodUnion, filterByMoods, cleanErr, journalLines, summarize };")();

const item = (id, moods, actif = true) => ({ drive_file_id: id, moods, actif });

test("stepOf : parcours normal", () => {
  assert.equal(L.stepOf(null), 1);
  for (const s of ["texte_en_cours", "texte_pret"]) assert.equal(L.stepOf({ statut: s }), 1);
  for (const s of ["selection_en_cours", "en_attente_validation"]) assert.equal(L.stepOf({ statut: s }), 2);
  for (const s of ["generation_en_cours", "premiere_prete", "galerie_prete", "budget_depasse", "termine"]) assert.equal(L.stepOf({ statut: s }), 3);
});

test("stepOf : une erreur reste à l'étape qui l'a produite", () => {
  assert.equal(L.stepOf({ statut: "erreur", erreur: "Texte : boom", titre: "" }), 1);
  assert.equal(L.stepOf({ statut: "erreur", erreur: "Texte : boom", titre: "T" }), 1);
  assert.equal(L.stepOf({ statut: "erreur", erreur: "Style : boom", titre: "T" }), 2);
  assert.equal(L.stepOf({ statut: "erreur", erreur: "", titre: "" }), 1);
});

test("moodUnion : union triée par fréquence, sans doublon", () => {
  const items = [item("a", ["parisian_chic", "vintage_retro"]), item("b", ["parisian_chic"]), item("c", ["streetwear_decontracte"])];
  assert.deepEqual(L.moodUnion(items, ["a", "b", "c"]), ["parisian_chic", "streetwear_decontracte", "vintage_retro"]);
  assert.deepEqual(L.moodUnion(items, ["a"]), ["parisian_chic", "vintage_retro"]);
  assert.deepEqual(L.moodUnion(items, []), []);
  assert.deepEqual(L.moodUnion(items, ["inconnu"]), []);
});

test("filterByMoods : au moins un mood coché, actifs seulement, aucun filtre = tout", () => {
  const items = [item("a", ["x", "y"]), item("b", ["y"]), item("c", ["z"]), item("d", ["x"], false)];
  assert.deepEqual(L.filterByMoods(items, ["x"]).map(i => i.drive_file_id), ["a"]);
  assert.deepEqual(L.filterByMoods(items, ["x", "z"]).map(i => i.drive_file_id), ["a", "c"]);
  assert.deepEqual(L.filterByMoods(items, []).map(i => i.drive_file_id), ["a", "b", "c"]);
});

test("cleanErr retire le préfixe d'étape", () => {
  assert.equal(L.cleanErr("Photos : délai dépassé"), "délai dépassé");
  assert.equal(L.cleanErr("Texte : x"), "x");
  assert.equal(L.cleanErr("autre"), "autre");
  assert.equal(L.cleanErr(undefined), "");
});

const job = (over) => Object.assign({ job_id: "j1", statut: "texte_en_cours", erreur: "", cout_total: 0, plans: [
  { plan: "porte_miroir", statut: "en_attente" }, { plan: "cintre", statut: "en_attente" }, { plan: "detail", statut: "en_attente" }] }, over);
const withPlans = (states) => ({ plans: ["porte_miroir", "cintre", "detail"].map((plan, i) => Object.assign({ plan, statut: "en_attente" }, states[i] || {})) });

test("journalLines : texte", () => {
  assert.deepEqual(L.journalLines(null, job()).map(l => l.text), ["Lecture des photos…"]);
  const l = L.journalLines(job(), job({ statut: "texte_pret" }));
  assert.deepEqual(l.map(x => [x.text, x.kind]), [["Annonce prête ✓", "ok"]]);
  assert.deepEqual(L.journalLines(job(), job()), []);
});

test("journalLines : sélection puis génération en deux temps", () => {
  assert.equal(L.journalLines(job({ statut: "texte_pret" }), job({ statut: "selection_en_cours" }))[0].text, "Recherche des inspirations dans la bibliothèque…");
  assert.equal(L.journalLines(job({ statut: "selection_en_cours" }), job({ statut: "en_attente_validation" }))[0].kind, "ok");
  assert.equal(L.journalLines(job({ statut: "en_attente_validation" }), job({ statut: "generation_en_cours" }))[0].text, "Génération de la photo portée (1/3)…");
  const prev = job({ statut: "generation_en_cours" });
  const cur = job({ statut: "premiere_prete", ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }]) });
  assert.deepEqual(L.journalLines(prev, cur).map(l => l.text), ["Photo « Porté » prête (1/3) ✓ 0.08 $", "Première photo prête : à toi de la valider."]);
  const s2 = job({ statut: "generation_en_cours", ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }]) });
  assert.equal(L.journalLines(cur, s2)[0].text, "Génération des photos 2/3 et 3/3…");
});

test("journalLines : galerie prête, erreurs de plan et d'étape", () => {
  const prev = job({ statut: "generation_en_cours", ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }, { statut: "pret", tentative: 1, cout_plan: 0.08 }]) });
  const cur = job({ statut: "galerie_prete", cout_total: 0.2402, ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }, { statut: "pret", tentative: 1, cout_plan: 0.08 }, { statut: "pret", tentative: 1, cout_plan: 0.08 }]) });
  assert.deepEqual(L.journalLines(prev, cur).map(l => l.text), ["Photo « Détail » prête (3/3) ✓ 0.08 $", "Les 3 photos sont prêtes ✓ (coût total 0.24 $)"]);
  const errPlan = job({ statut: "galerie_prete", ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }, { statut: "erreur", erreur: "Photos : délai dépassé" }]) });
  assert.ok(L.journalLines(job({ statut: "generation_en_cours" }), errPlan).some(l => l.kind === "err" && l.text === "⚠ Photo « Sur cintre » : délai dépassé"));
  const errJob = L.journalLines(job(), job({ statut: "erreur", erreur: "Texte : boom" }));
  assert.ok(errJob.some(l => l.kind === "err" && l.text === "⚠ Texte : boom"));
});

test("journalLines : régénération d'une photo", () => {
  const ready = withPlans([{ statut: "pret", tentative: 1 }, { statut: "pret", tentative: 1 }, { statut: "pret", tentative: 1 }]);
  const l = L.journalLines(job({ statut: "galerie_prete", ...ready }), job({ statut: "generation_en_cours", ...ready }));
  assert.equal(l[0].text, "Régénération d'une photo…");
});

test("summarize : période, totaux, images et régénérations", () => {
  const now = new Date("2026-09-25T12:00:00Z").getTime();
  const jobs = [
    { created_at: "2026-09-24T10:00:00Z", cout_texte: 0.0002, cout_images: 0.24, cout_total: 0.2402, nb_images: 3, nb_regenerations: 0 },
    { created_at: "2026-09-10T10:00:00Z", cout_texte: 0.0002, cout_images: 0.4, cout_total: 0.4002, nb_images: 5, nb_regenerations: 2 },
    { created_at: "2026-08-01T10:00:00Z", cout_texte: 0, cout_images: 0, cout_total: 0, nb_images: 0, nb_regenerations: 0 }
  ];
  const s7 = L.summarize(jobs, 7, now), s30 = L.summarize(jobs, 30, now), all = L.summarize(jobs, 0, now);
  assert.equal(s7.fiches, 1); assert.equal(s30.fiches, 2); assert.equal(all.fiches, 3);
  assert.equal(s30.images, 8); assert.equal(s30.regenerations, 2);
  assert.equal(Math.round(s30.cout_total * 10000), 6404);
  assert.equal(all.list.length, 3);
});
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

```bash
cd poc-annonces-n8n && node --test scripts/test_front_logic.mjs
```

Expected : FAIL (`bloc // <logic> introuvable`).

- [ ] **Step 3: Écrire le bloc de logique dans `front/index.html`**

Juste après la ligne `"use strict";` du `<script>`, insérer (et **supprimer** la constante `PLAN_LABELS` définie plus bas, elle est déplacée ici) :

```js
// <logic>
const PLAN_ORDER = ["porte_miroir", "cintre", "detail"];
const PLAN_LABELS = { porte_miroir: "Porté", cintre: "Sur cintre", detail: "Détail" };
const cleanErr = m => String(m || "").replace(/^(Texte|Style|Photos) : /, "");

function stepOf(j) {
  if (!j) return 1;
  const s = j.statut;
  if (s === "texte_en_cours" || s === "texte_pret") return 1;
  if (s === "selection_en_cours" || s === "en_attente_validation") return 2;
  if (["generation_en_cours", "premiere_prete", "galerie_prete", "budget_depasse", "termine"].includes(s)) return 3;
  if (s === "erreur") return /^Style/.test(j.erreur || "") && j.titre ? 2 : 1;
  return 1;
}

function moodUnion(items, selectedIds) {
  const count = new Map();
  for (const id of selectedIds) {
    const it = items.find(i => i.drive_file_id === id);
    for (const m of (it && it.moods) || []) count.set(m, (count.get(m) || 0) + 1);
  }
  return [...count.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(e => e[0]);
}

function filterByMoods(items, moods) {
  return items.filter(i => i.actif && (!moods.length || (i.moods || []).some(m => moods.includes(m))));
}

function journalLines(prev, cur) {
  const out = [], add = (text, kind) => out.push({ text, kind: kind || "info" });
  const same = !!prev && prev.job_id === cur.job_id;
  const was = same ? prev.statut : null, now = cur.statut;
  const isReady = p => p.statut === "pret";
  for (const p of cur.plans || []) {
    if (!same) break;                       // au rechargement d'une fiche on ne rejoue pas chaque photo
    const before = (prev.plans || []).find(x => x.plan === p.plan) || {};
    const n = PLAN_ORDER.indexOf(p.plan) + 1;
    if (isReady(p) && !(isReady(before) && before.tentative === p.tentative)) add("Photo « " + PLAN_LABELS[p.plan] + " » prête (" + n + "/3) ✓ " + Number(p.cout_plan || 0).toFixed(2) + " $", "ok");
    else if (p.statut === "erreur" && !(before.statut === "erreur" && before.erreur === p.erreur)) add("⚠ Photo « " + PLAN_LABELS[p.plan] + " » : " + cleanErr(p.erreur), "err");
  }
  if (now !== was) {
    const ready = (cur.plans || []).filter(isReady).length;
    if (now === "texte_en_cours") add("Lecture des photos…");
    else if (now === "texte_pret") add("Annonce prête ✓", "ok");
    else if (now === "selection_en_cours") add("Recherche des inspirations dans la bibliothèque…");
    else if (now === "en_attente_validation") add("Inspirations proposées : à toi de choisir ✓", "ok");
    else if (now === "generation_en_cours") add(ready === 0 ? "Génération de la photo portée (1/3)…" : ready === 1 ? "Génération des photos 2/3 et 3/3…" : ready >= 3 ? "Régénération d'une photo…" : "Nouvelle tentative…");
    else if (now === "premiere_prete") add("Première photo prête : à toi de la valider.", "ok");
    else if (now === "galerie_prete") add("Les 3 photos sont prêtes ✓ (coût total " + Number(cur.cout_total || 0).toFixed(2) + " $)", "ok");
    else if (now === "budget_depasse") add("Plafond de coût atteint.", "err");
    else if (now === "termine") add("Fiche clôturée. Merci !", "ok");
  }
  if (cur.erreur && (!same || prev.erreur !== cur.erreur)) add("⚠ " + cur.erreur, "err");
  return out;
}

function summarize(jobs, days, now) {
  const since = days ? now - days * 86400000 : 0;
  const list = jobs.filter(j => new Date(j.created_at).getTime() >= since);
  const sum = k => list.reduce((a, j) => a + Number(j[k] || 0), 0);
  return { fiches: list.length, images: sum("nb_images"), regenerations: sum("nb_regenerations"),
    cout_texte: sum("cout_texte"), cout_images: sum("cout_images"), cout_total: sum("cout_total"), list };
}
// </logic>
```

Note : `stepOf` ci-dessus renvoie 2 uniquement pour une erreur `Style`, 1 sinon (le test `Texte : boom` avec `titre` renvoie bien 1).

- [ ] **Step 4: Lancer les tests**

```bash
cd poc-annonces-n8n && node --test scripts/test_front_logic.mjs
```

Expected : tous les tests `pass` (9 tests).

- [ ] **Step 5: Vérifier que la page se charge toujours**

Ouvrir `http://localhost:8765` dans le navigateur intégré, `read_console_messages` avec `onlyErrors: true`. Expected : aucune erreur JS (la page peut demander le secret).

- [ ] **Step 6: Commit**

```bash
git add poc-annonces-n8n/front/index.html poc-annonces-n8n/scripts/test_front_logic.mjs
git commit -m "feat(poc-annonces-n8n): logique pure du front (etapes, moods, journal, historique) et tests

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Navigation, stepper, journal, réglages fusionnés

**Files:**
- Modify: `poc-annonces-n8n/front/index.html`

**Interfaces:**
- Consumes : `stepOf`, `journalLines` (Task 8).
- Produces : onglets `#tab-creer`, `#tab-historique`, `#tab-reglages` ; `showTab(name)` avec `name ∈ creer|historique|reglages` ; `renderCreate()` ; `pushJournal(text, kind)`, `renderJournal()`, `resetJournal(jobId)` ; conteneurs d'étape `#stepForm`, `#stepText`, `#stepInspi`, `#stepPhotos`, `#journalCard`, `#journal`, `#newBar`, `#newBtn`, `#jobRef` ; dans Réglages : `<details>` `#dConnexion`, `#dProfil`, `#dBiblio`, `#dPrompts` ; les contrôles de connexion `#setBase`, `#setSecret`, `#setSave`.

- [ ] **Step 1: CSS**

Ajouter dans `<style>`, avant `</style>` :

```css
  .stepper { display: flex; gap: 8px; margin: 0 0 16px; flex-wrap: wrap; }
  .step { flex: 1; min-width: 140px; display: flex; gap: 8px; align-items: center; padding: 10px 12px; border: 1px solid var(--line); border-radius: 10px; background: var(--card); color: var(--muted); }
  .step .n { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; background: var(--chip); font-size: 12px; font-weight: 600; }
  .step.active { color: var(--ink); border-color: var(--accent); font-weight: 600; }
  .step.active .n { background: var(--accent); color: var(--accent-ink); }
  .step.done { color: var(--ink); }
  .step.done .n { background: var(--good); color: #fff; }
  #journal { font: 12.5px/1.6 ui-monospace, monospace; color: var(--muted); max-height: 190px; overflow: auto; }
  #journal .l.err { color: var(--bad); }
  #journal .l.ok { color: var(--muted); }
  #journal .l:last-child { color: var(--ink); }
  details.card > summary { cursor: pointer; font-weight: 600; font-size: 16px; }
  details.card[open] > summary { margin-bottom: 12px; }
  .hist-row { display: grid; grid-template-columns: 64px 1fr auto; gap: 12px; align-items: center; cursor: pointer; }
  .hist-row img { width: 64px; height: 84px; object-fit: cover; border-radius: 8px; background: var(--chip); }
  .hist-totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
  .hist-totals .k { font-size: 12px; color: var(--muted); }
  .hist-totals .v { font-size: 20px; font-weight: 650; }
```

- [ ] **Step 2: HTML — remplacer le contenu de `<header>` et ouvrir les 3 onglets**

Remplacer le bloc `<header> … </header>` par :

```html
<header>
  <h1>🧥 Fiches Vinted</h1>
  <nav id="tabs">
    <button data-tab="creer" class="on">Créer</button>
    <button data-tab="historique">Historique</button>
    <button data-tab="reglages">Réglages</button>
  </nav>
  <span class="grow"></span>
  <label style="margin:0" class="muted">Utilisateur
    <select id="userSel" style="width:auto;display:inline-block"></select>
  </label>
</header>
```

Dans `<main>`, remplacer le début `<div id="tab-fiche">` par :

```html
  <!-- ========== CRÉER ========== -->
  <div id="tab-creer">
    <div class="stepper" id="stepper">
      <div class="step active" data-step="1"><span class="n">1</span> Annonce</div>
      <div class="step" data-step="2"><span class="n">2</span> Inspirations</div>
      <div class="step" data-step="3"><span class="n">3</span> Photos de l'annonce</div>
    </div>
    <div class="row hidden" id="newBar" style="margin-bottom:12px"><button class="btn ghost" id="newBtn">＋ Nouvelle annonce</button><span class="muted" id="jobRef"></span></div>
```

Le `<section class="card" id="formCard">` existant devient `<section class="card" id="stepForm">` (mêmes champs ; retirer le paragraphe `Le mood des photos se choisit…` et remplacer le titre `<h2>1. Photos du vêtement</h2>` par `<h2>Annonce</h2>`, bouton `Créer la fiche` → `Créer l'annonce`).

Le `<section class="card hidden" id="jobCard"> … </section>` (texte + style + relecture) est **supprimé** et remplacé par les quatre blocs vides suivants (remplis aux Task 10 à 12), placés juste après `#stepForm` :

```html
    <section class="card hidden" id="stepText"></section>
    <section class="card hidden" id="stepInspi"></section>
    <section class="card hidden" id="stepPhotos"></section>
    <section class="card hidden" id="journalCard"><h3>Suivi</h3><div id="journal"></div></section>
  </div>
```

- [ ] **Step 3: HTML — onglets Historique et Réglages**

Supprimer les blocs `#tab-galerie`, `#tab-biblio`, `#tab-profil`, `#tab-prompts` de leur emplacement actuel et les recréer ainsi (le contenu interne de chaque ancien bloc est déplacé tel quel dans le `<details>` correspondant ; les `id` internes ne changent pas) :

```html
  <!-- ========== HISTORIQUE ========== -->
  <div id="tab-historique" class="hidden"></div>

  <!-- ========== RÉGLAGES ========== -->
  <div id="tab-reglages" class="hidden">
    <details class="card" id="dConnexion">
      <summary>Connexion</summary>
      <label>URL des webhooks n8n</label>
      <input type="text" id="setBase">
      <label>Secret (en-tête X-VFN-Secret)</label>
      <input type="password" id="setSecret" autocomplete="off">
      <p class="muted">Le secret est gardé dans ce navigateur uniquement (localStorage).</p>
      <div class="row" style="margin-top:14px"><button class="btn" id="setSave">Enregistrer</button></div>
    </details>
    <details class="card" id="dProfil">
      <summary>Profil de rédaction</summary>
      <!-- contenu de l'ancien #tab-profil : le <section class="card"> et #profProposal, sans le <h2> -->
    </details>
    <details class="card" id="dBiblio">
      <summary>Bibliothèque d'inspirations</summary>
      <!-- contenu de l'ancien #tab-biblio : les 2 <section>, #lib -->
    </details>
    <details class="card" id="dPrompts">
      <summary>Prompts</summary>
      <p class="muted">Modifier un prompt change immédiatement les prochaines générations, et on peut toujours revenir à une version précédente. À ne toucher que si tu sais ce que tu fais.</p>
      <!-- contenu de l'ancien #tab-prompts : #pName, #pDays, #pPropose, #pMsg, #pProposal, #pVersions -->
    </details>
  </div>
```

Supprimer le bloc `<dialog id="settings"> … </dialog>` et le bouton `#settingsBtn` (déjà retiré du header).

- [ ] **Step 4: JS — navigation**

Remplacer les fonctions `showTab`, l'écouteur des onglets, `openSettings`, `#settingsBtn`, `#setCancel`, `#setSave`, et `start()` par :

```js
// ---------- onglets ----------
function showTab(name) {
  for (const t of ["creer", "historique", "reglages"]) $("#tab-" + t).classList.toggle("hidden", t !== name);
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === name));
  store.set("tab", name);
  if (name === "historique") loadHistory();
}
document.querySelectorAll("#tabs button").forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));

// Réglages : chargement à l'ouverture de chaque section
$("#dProfil").addEventListener("toggle", () => { if ($("#dProfil").open) loadProfile(); });
$("#dBiblio").addEventListener("toggle", () => { if ($("#dBiblio").open && !LIB) loadLibrary(); });
$("#dPrompts").addEventListener("toggle", () => { if ($("#dPrompts").open && !PROMPTS) loadPrompts(); });

function openSettings() { $("#setBase").value = base(); $("#setSecret").value = store.get("secret") || ""; showTab("reglages"); $("#dConnexion").open = true; }
$("#setSave").addEventListener("click", () => {
  store.set("base", $("#setBase").value.trim() || DEFAULT_BASE); store.set("secret", $("#setSecret").value.trim());
  toast("Connexion enregistrée"); start();
});
```

Et `start()` :

```js
async function start() {
  if (!store.get("secret")) { openSettings(); return; }
  try { await loadConfig(); } catch (e) { toast(e.message, 6000); openSettings(); return; }
  showTab(store.get("tab") === "historique" || store.get("tab") === "reglages" ? store.get("tab") : "creer");
  renderCreate();
  const last = store.get("job");
  if (last) refreshJob(last).catch(() => {});
}
```

Dans la fonction `loadProfile`, `$("#profUser")` disparaît avec le `<h2>` : le remplacer par `$("#profUser")` toujours présent dans un `<p class="muted">Profil de <b id="profUser"></b></p>` au début du `<details id="dProfil">`. Le gestionnaire `#userSel change` existant recharge le profil si `#dProfil` est ouvert : remplacer sa condition `!$("#tab-profil").classList.contains("hidden")` par `$("#dProfil").open`. Dans `loadLibrary`, remplacer `showTab`-dépendances : rien d'autre.

- [ ] **Step 5: JS — état, journal, rendu de l'étape courante**

Remplacer `STATUS_LABELS` par :

```js
const STATUS_LABELS = {
  texte_en_cours: "Rédaction de l'annonce…", texte_pret: "Annonce prête", selection_en_cours: "Recherche des inspirations…",
  en_attente_validation: "À toi de choisir les inspirations", generation_en_cours: "Génération des photos…",
  premiere_prete: "Première photo prête", galerie_prete: "Photos prêtes", budget_depasse: "Plafond de coût atteint", termine: "Terminée", erreur: "Erreur"
};
```

Remplacer `draftFor` et le commentaire associé par :

```js
// Brouillon de la fiche courante : jamais écrasé par les rafraîchissements de statut.
let draft = null;
function draftFor(j) {
  if (!draft || draft.jobId !== j.job_id) draft = { jobId: j.job_id, initSel: false, sel: { vision: [], texte: [] }, selTouched: false, pending: [], moods: [], garment: null, garmentDirty: false, mannequin: null, mannequinDirty: false };
  const d = draft;
  if (!d.garmentDirty && j.garment_en != null) d.garment = j.garment_en;
  if (!d.mannequinDirty && j.mannequin_desc != null) d.mannequin = j.mannequin_desc;
  if (j.statut === "en_attente_validation" && !d.initSel) {
    d.initSel = true; d.selTouched = false;
    d.sel.vision = (j.decor_refs || []).map(r => r.file_id).slice(0, MAX_VISION);
    d.sel.texte = (j.inspi_texte || []).map(r => r.file_id).filter(id => !d.sel.vision.includes(id)).slice(0, MAX_TEXTE);
  }
  return d;
}
```

Supprimer `moodIds`-dépendances inutiles : conserver `moodIds()` (toujours utilisé pour `moods_autorises`). Ajouter le journal après `setStatus` :

```js
// ---------- journal ----------
let journal = { jobId: null, lines: [] };
function resetJournal(jobId) { journal = { jobId, lines: [] }; }
function pushJournal(text, kind) {
  const last = journal.lines[journal.lines.length - 1];
  if (last && last.text === text) return;
  const t = new Date(); const hh = String(t.getHours()).padStart(2, "0") + ":" + String(t.getMinutes()).padStart(2, "0") + ":" + String(t.getSeconds()).padStart(2, "0");
  journal.lines.push({ text, kind: kind || "info", hh });
}
function renderJournal() {
  const box = $("#journal"); box.innerHTML = "";
  for (const l of journal.lines) box.append(h("div", { class: "l " + l.kind }, l.hh + "  " + l.text));
  box.scrollTop = box.scrollHeight;
}
let textTimer = null;
function armTextTimer(jobId) {              // 2ᵉ message du texte : temporisé (un seul état côté n8n)
  clearTimeout(textTimer);
  textTimer = setTimeout(() => { if (job && job.job_id === jobId && job.statut === "texte_en_cours") { pushJournal("Rédaction de l'annonce…"); renderJournal(); } }, 3000);
}
```

Dans `refreshJob`, remplacer les lignes `pollFails = 0; job = j; store.set("job", id); renderAll();` par :

```js
  pollFails = 0;
  const prev = job;
  if (!prev || prev.job_id !== j.job_id) resetJournal(j.job_id);
  job = j; store.set("job", id);
  for (const l of journalLines(prev && prev.job_id === j.job_id ? prev : null, j)) pushJournal(l.text, l.kind);
  if (j.statut === "texte_en_cours") armTextTimer(j.job_id);
  renderCreate();
```

Remplacer `function renderAll() { renderFiche(); renderGallery(); }` par :

```js
function renderCreate() {
  const step = stepOf(job);
  document.querySelectorAll("#stepper .step").forEach(el => {
    const n = Number(el.dataset.step);
    el.classList.toggle("active", n === step);
    el.classList.toggle("done", !!job && n < step);
  });
  $("#newBar").classList.toggle("hidden", !job);
  $("#jobRef").textContent = job ? "Annonce " + job.job_id : "";
  $("#stepForm").classList.toggle("hidden", !!job);
  $("#stepText").classList.toggle("hidden", !job || step !== 1);
  $("#stepInspi").classList.toggle("hidden", !job || step !== 2);
  $("#stepPhotos").classList.toggle("hidden", !job || step !== 3);
  $("#journalCard").classList.toggle("hidden", !job);
  if (!job) return;
  const d = draftFor(job);
  if (step === 1) renderText(d); else if (step === 2) renderInspi(d); else renderPhotos(d);
  renderJournal();
}
function renderText() {}     // remplacée en Task 10
function renderInspi() {}    // remplacée en Task 11
function renderPhotos() {}   // remplacée en Task 12
$("#newBtn").addEventListener("click", () => {
  stopPoll(); clearTimeout(textTimer); job = null; currentJobId = null; draft = null; store.set("job", "");
  globalNote = null; globalReasons = new Set(); resetJournal(null); renderCreate();
});
```

Supprimer l'ancien `renderFiche`, `syncGarment`, les écouteurs `.garment-en`, `renderStyleGrid`, `renderReview`, `renderGallery`, `renderGlobal`, `ratingWidget`, `origFigure`, `toggleInspi`, `useAsInspi`, `pickMood`, `preselect`, `inspiInfo` **seulement à la fin de la Task 12** : d'ici là ils restent en place mais inactifs (leurs éléments DOM n'existent plus, donc ne les appeler nulle part) ; pour éviter les erreurs de chargement dues aux écouteurs (`$("#refineBtn")`, `$("#allTypes")`, `$("#reviewBtn")`, `$("#validateBtn")`, `$("#rerollBtn")`, `$("#styleBtn")`, `$("#globalSend")`, `$("#copyTitle")`…, `$("#openBtn")`, `$("#ficheUpBtn")`, `$("#moodSelect")`, `$("#mannequinDesc")`, `$("#photoSansMiroir")`), **les supprimer dès maintenant** avec leurs blocs. Ces écouteurs sont réécrits aux Tasks 10 à 12 avec les nouveaux éléments.

- [ ] **Step 6: Vérifier**

```bash
cd poc-annonces-n8n && node --test scripts/test_front_logic.mjs
```

Expected : tests `pass`. Puis dans le navigateur intégré (`http://localhost:8765`, secret saisi dans Réglages > Connexion) : 3 boutons de navigation seulement ; « Créer » montre le stepper (étape 1 active) et le formulaire ; « Réglages » montre 4 sections repliées ; ouvrir « Bibliothèque » charge la grille ; ouvrir « Prompts » charge la liste ; `read_console_messages` `onlyErrors` : aucune erreur.

- [ ] **Step 7: Commit**

```bash
git add poc-annonces-n8n/front/index.html
git commit -m "feat(poc-annonces-n8n): navigation en 3 entrees, stepper, journal, reglages regroupes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: Étape 1 — Annonce

**Files:**
- Modify: `poc-annonces-n8n/front/index.html`

**Interfaces:**
- Consumes : `renderText(d)` (stub de la Task 9), `draftFor`, `refreshJob`, `armTextTimer`.
- Produces : `renderText(d)` complète ; boutons `#refineBtn`, `#retryTextBtn`, `#styleBtn`, `#garmentToggle`, textarea `#garmentEn` (brouillon `d.garment`).

- [ ] **Step 1: HTML de `#stepText`**

Remplacer `<section class="card hidden" id="stepText"></section>` par :

```html
    <section class="card hidden" id="stepText">
      <div class="row"><h2 class="grow">Annonce</h2><span class="status" id="jobStatus"></span></div>
      <div id="jobError" class="bad"></div>
      <div class="row hidden" id="retryTextBar"><button class="btn" id="retryTextBtn">Réessayer</button></div>
      <div id="textBlock" class="hidden">
        <h3 id="titre"></h3>
        <p class="desc" id="desc"></p>
        <div class="row">
          <button class="btn ghost" id="copyTitle">Copier le titre</button>
          <button class="btn ghost" id="copyDesc">Copier la description</button>
        </div>
        <label>Un changement à demander ?</label>
        <textarea id="feedbackText" placeholder="Ex. : c'est de la viscose, ton plus sobre, mentionne la coupe"></textarea>
        <div class="row" style="margin-top:8px">
          <button class="btn ghost" id="refineBtn">Mettre à jour le texte</button>
          <button class="linkbtn" id="garmentToggle">Modifier la description du vêtement pour les photos</button>
          <span class="grow"></span>
          <button class="btn" id="styleBtn">Choisir les inspirations →</button>
        </div>
        <div id="garmentBox" class="hidden">
          <label>Description du vêtement pour les photos <span class="muted">(anglais, modifiable)</span></label>
          <textarea id="garmentEn"></textarea>
        </div>
      </div>
    </section>
```

- [ ] **Step 2: JS**

Remplacer le stub `function renderText() {}` par :

```js
function renderText(d) {
  setStatus($("#jobStatus"), job.statut);
  const isErr = job.statut === "erreur";
  $("#jobError").textContent = isErr ? job.erreur : "";
  $("#retryTextBar").classList.toggle("hidden", !isErr);
  const ready = !!job.titre;
  $("#textBlock").classList.toggle("hidden", !ready);
  if (!ready) return;
  $("#titre").textContent = job.titre; $("#desc").textContent = job.description;
  const busy = BUSY.includes(job.statut);
  for (const id of ["refineBtn", "styleBtn"]) $("#" + id).disabled = busy;
  if (document.activeElement !== $("#garmentEn") && $("#garmentEn").value !== (d.garment || "")) $("#garmentEn").value = d.garment || "";
}
$("#garmentEn").addEventListener("input", () => { if (draft) { draft.garment = $("#garmentEn").value; draft.garmentDirty = true; } });
$("#garmentToggle").addEventListener("click", () => $("#garmentBox").classList.toggle("hidden"));
$("#refineBtn").addEventListener("click", async () => {
  const msg = $("#feedbackText").value.trim(); if (!msg) return toast("Écris ce que tu veux changer");
  try { await api("POST", "/job/texte", { job_id: job.job_id, message: msg }); $("#feedbackText").value = ""; await refreshJob(job.job_id); } catch (e) { toast(e.message); }
});
$("#retryTextBtn").addEventListener("click", async () => {
  try { await api("POST", "/job/texte", { job_id: job.job_id, retry: true }); await refreshJob(job.job_id); } catch (e) { toast(e.message); }
});
$("#copyTitle").addEventListener("click", () => copy(job.titre, "Titre"));
$("#copyDesc").addEventListener("click", () => copy(job.description, "Description"));
$("#styleBtn").addEventListener("click", startStyle);
```

Et la création (remplacer les lignes concernées de `#createBtn`) : conserver le handler existant, en remplaçant la ligne `draft = null; globalNote = null; …; $("#globalComment").value = "";` par `draft = null; globalNote = null; globalReasons = new Set();` (le champ `#globalComment` est recréé en Task 12), et le libellé du message `Envoi des photos…` reste. Remplacer aussi `fd.append("moods_autorises", JSON.stringify(moodIds()));  // le mood se choisit à l'étape style` par `fd.append("moods_autorises", JSON.stringify(moodIds()));`.

Ajouter la fonction `copy` si elle a été supprimée avec les anciens écouteurs :

```js
const copy = async (text, what) => { try { await navigator.clipboard.writeText(text); toast(what + " copié"); } catch (e) { toast("Copie impossible"); } };
```

et `startStyle` (remplace l'ancienne) :

```js
async function startStyle() {
  try {
    await api("POST", "/job/style", { job_id: job.job_id, moods_autorises: moodIds() });
    if (draft && draft.jobId === job.job_id) draft.initSel = false;   // repartir de la proposition
    await refreshJob(job.job_id);
  } catch (e) { toast(e.message); }
}
```

- [ ] **Step 3: Vérifier (aucun coût ; fiche de test existante)**

Dans la console du navigateur intégré (`javascript_tool`) : `store.set("job","muftpawvta7x"); start()`. Puis vérifier que `#stepper` marque l'étape 3 (fiche en `galerie_prete`) — l'étape 1 est vérifiée avec une nouvelle fiche à la Task 16. Vérifier sans réseau : `job = { job_id:"x", statut:"texte_pret", titre:"T", description:"D", garment_en:"g", plans:[] }; draft=null; renderCreate();` → `#stepText` visible, `#titre` = `T`, `#garmentBox` masquée ; clic sur `#garmentToggle` → visible.

```bash
cd poc-annonces-n8n && node --test scripts/test_front_logic.mjs
```

Expected : `pass`, et `read_console_messages` sans erreur.

- [ ] **Step 4: Commit**

```bash
git add poc-annonces-n8n/front/index.html
git commit -m "feat(poc-annonces-n8n): etape Annonce (texte, retry, description anglaise masquee)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 11: Étape 2 — Inspirations

**Files:**
- Modify: `poc-annonces-n8n/front/index.html`

**Interfaces:**
- Consumes : `filterByMoods`, `moodUnion`, `LIB` / `loadLibrary()`, `draftFor`, `startStyle`, `moodChip`, `lazyImg`, `MAX_VISION`, `MAX_TEXTE`.
- Produces : `renderInspi(d)` ; `$("#validateBtn")` lance `POST /job/valider` avec `plans: ["porte_miroir"]` et `mood = moodUnion(...).join(", ")`.

- [ ] **Step 1: HTML de `#stepInspi`**

Remplacer `<section class="card hidden" id="stepInspi"></section>` par :

```html
    <section class="card hidden" id="stepInspi">
      <div class="row"><h2 class="grow">Inspirations</h2><span class="status" id="inspiStatus"></span></div>
      <div id="inspiError" class="bad"></div>
      <div class="row hidden" id="retryStyleBar"><button class="btn" id="retryStyleBtn">Réessayer</button></div>
      <div id="warnings" class="warn"></div>
      <p class="muted">Filtre par ambiance (plusieurs possibles ; aucun = toute la bibliothèque). Choisis 1 ou 2 photos <b style="color:var(--accent)">principales</b> (vues par le générateur) et jusqu'à 3 <b style="color:var(--warn)">secondaires</b> (seule leur description est utilisée).</p>
      <div class="chips" id="moodChips"></div>
      <div class="row"><span class="muted grow" id="gridCount"></span><span class="muted" id="selCount"></span></div>
      <div class="grid-inspi" id="styleGrid"></div>
      <div class="row" style="margin-top:10px">
        <label style="margin:0">Ajouter une inspiration à la bibliothèque et à cette annonce</label>
        <input type="file" id="ficheUpFiles" accept="image/*" multiple style="width:auto">
        <button class="btn ghost" id="ficheUpBtn">Envoyer</button><span class="muted" id="ficheUpMsg"></span>
      </div>
      <div class="row" style="margin-top:10px"><button class="linkbtn" id="mannToggle">Modifier la description du mannequin (photo portée)</button></div>
      <div id="mannBox" class="hidden"><textarea id="mannequinDesc"></textarea></div>
      <div class="row" style="margin-top:14px">
        <button class="btn ghost" id="rerollBtn">Revenir à la proposition</button>
        <span class="grow"></span>
        <span class="muted">≈ 0,08 $ pour la première photo</span>
        <button class="btn" id="validateBtn">Générer la première photo</button>
      </div>
    </section>
```

- [ ] **Step 2: JS**

Remplacer le stub `function renderInspi() {}` et ajouter (les fonctions `libById`, `moodChip`, `loadLibrary` existent déjà ; supprimer l'ancien `inspiInfo` ; `loadLibrary` garde son comportement mais ne doit plus appeler de `#fGenre`… : inchangé car ces contrôles restent dans Réglages) :

```js
const libById = id => (LIB || []).find(i => i.drive_file_id === id);
let libLoading = false;

function toggleInspi(fileId, kind) {
  const sel = draft.sel; draft.selTouched = true;
  const other = kind === "vision" ? "texte" : "vision";
  const max = kind === "vision" ? MAX_VISION : MAX_TEXTE;
  if (sel[kind].includes(fileId)) sel[kind] = sel[kind].filter(id => id !== fileId);
  else if (sel[kind].length < max) { sel[other] = sel[other].filter(id => id !== fileId); sel[kind].push(fileId); }
  else toast("Maximum " + max + " " + (kind === "vision" ? "principales" : "secondaires"));
  renderInspi(draft);
}

function renderInspi(d) {
  setStatus($("#inspiStatus"), job.statut);
  const isErr = job.statut === "erreur";
  $("#inspiError").textContent = isErr ? job.erreur : "";
  $("#retryStyleBar").classList.toggle("hidden", !isErr);
  const waiting = job.statut === "en_attente_validation";
  $("#warnings").textContent = (job.avertissements || []).join(" — ");
  for (const id of ["validateBtn", "rerollBtn"]) $("#" + id).disabled = !waiting;
  if (!LIB && !libLoading) { libLoading = true; loadLibrary().finally(() => { libLoading = false; if (job && stepOf(job) === 2) renderInspi(draftFor(job)); }); }
  if (document.activeElement !== $("#mannequinDesc") && $("#mannequinDesc").value !== (d.mannequin || "")) $("#mannequinDesc").value = d.mannequin || "";

  const chips = $("#moodChips"); chips.innerHTML = "";
  for (const m of CONFIG.moods) chips.append(moodChip(m, d.moods.includes(m.id), () => {
    d.moods = d.moods.includes(m.id) ? d.moods.filter(x => x !== m.id) : [...d.moods, m.id]; renderInspi(d);
  }));
  const box = $("#styleGrid"); box.innerHTML = "";
  if (!LIB) { box.append(h("span", { class: "muted" }, "Chargement de la bibliothèque…")); $("#gridCount").textContent = ""; }
  else {
    const sel = d.sel, chosen = id => sel.vision.includes(id) || sel.texte.includes(id);
    const shown = filterByMoods(LIB, d.moods);
    const list = [...shown.filter(i => chosen(i.drive_file_id)), ...shown.filter(i => !chosen(i.drive_file_id)).sort((a, b) => (b.utilisations || 0) - (a.utilisations || 0))];
    for (const id of [...sel.vision, ...sel.texte]) if (!list.some(i => i.drive_file_id === id)) { const it = libById(id); if (it) list.unshift(it); }
    $("#gridCount").textContent = list.length + " photo(s)" + (d.moods.length ? " · " + d.moods.map(m => m.replaceAll("_", " ")).join(" + ") : " · toute la bibliothèque");
    for (const pid of d.pending) if (!libById(pid)) box.append(h("div", { class: "card item off" }, lazyImg(pid), h("div", { class: "muted" }, "indexation en cours")));
    if (!list.length) box.append(h("span", { class: "muted" }, "Aucune photo pour ce filtre : retire une ambiance."));
    for (const it of list) {
      const id = it.drive_file_id, isV = sel.vision.includes(id), isT = sel.texte.includes(id);
      const card = h("div", { class: "card item" + (isV ? " vision" : isT ? " texte" : "") });
      const mchips = h("div", { class: "chips" }, (it.moods || []).map(m => h("span", { class: "chip static" + (d.moods.includes(m) ? " on" : "") }, m.replaceAll("_", " "))));
      const descBox = h("div", { class: "hidden" });
      const ta = h("textarea", {}); ta.value = it.description_en || "";
      const save = h("button", { class: "btn ghost", style: "margin-top:4px", onclick: async () => {
        try { const r = await api("POST", "/library/update", { drive_file_id: id, description_en: ta.value }); it.description_en = r.description_en; toast("Description enregistrée"); } catch (e) { toast(e.message); }
      } }, "Enregistrer");
      descBox.append(ta, save);
      card.append(lazyImg(id), mchips,
        h("div", { class: "muted" }, it.type_vetement + " · utilisée " + (it.utilisations || 0) + " fois"),
        h("div", { class: "seg" },
          h("button", { class: "v" + (isV ? " on" : ""), title: "Image envoyée au générateur (2 max)", onclick: () => toggleInspi(id, "vision") }, "Principale"),
          h("button", { class: "t" + (isT ? " on" : ""), title: "Seule sa description est envoyée (3 max)", onclick: () => toggleInspi(id, "texte") }, "Secondaire")),
        h("button", { class: "linkbtn", onclick: () => descBox.classList.toggle("hidden") }, "Modifier la description"),
        descBox);
      box.append(card);
    }
  }
  $("#selCount").textContent = "Sélection : " + d.sel.vision.length + "/" + MAX_VISION + " principales · " + d.sel.texte.length + "/" + MAX_TEXTE + " secondaires";
}

$("#mannToggle").addEventListener("click", () => $("#mannBox").classList.toggle("hidden"));
$("#mannequinDesc").addEventListener("input", () => { if (draft) { draft.mannequin = $("#mannequinDesc").value; draft.mannequinDirty = true; } });
$("#retryStyleBtn").addEventListener("click", startStyle);
$("#rerollBtn").addEventListener("click", startStyle);

$("#validateBtn").addEventListener("click", async () => {
  const d = draft; if (!d || !job) return;
  const ids = [...d.sel.vision, ...d.sel.texte];
  if (!ids.length && !confirm("Aucune inspiration choisie. Générer quand même ?")) return;
  const mood = moodUnion(LIB || [], ids).join(", ");
  $("#validateBtn").disabled = true;
  try {
    await api("POST", "/job/valider", {
      job_id: job.job_id, mood, decor_refs: d.sel.vision, inspi_texte: d.sel.texte,
      garment_en: d.garment != null ? d.garment : (job.garment_en || ""), mannequin_desc: d.mannequin != null ? d.mannequin : (job.mannequin_desc || ""),
      texte_visible: !!job.texte_visible, plans: ["porte_miroir"]
    });
    await refreshJob(job.job_id);
  } catch (e) { toast(e.message, 6000); }
  $("#validateBtn").disabled = false;
});
```

Reprendre à l'identique, avec les nouveaux éléments, le handler d'envoi d'inspiration depuis l'annonce (`$("#ficheUpBtn")`), tel qu'il existait, en remplaçant les appels `renderStyleGrid()` par `renderInspi(draftFor(job))` et les tests `job.statut === "en_attente_validation"` par `stepOf(job) === 2`. Cela conserve la sélection des nouvelles photos indexées.

- [ ] **Step 3: Vérifier la logique et l'affichage (sans coût)**

```bash
cd poc-annonces-n8n && node --test scripts/test_front_logic.mjs
```

Dans le navigateur intégré, après chargement de la bibliothèque (Réglages > Bibliothèque une fois, ou `loadLibrary()` en console), exécuter :

```js
job = { job_id:"x", statut:"en_attente_validation", genre:"femme", type_vetement:"veste", titre:"T", decor_refs:[], inspi_texte:[], avertissements:[], plans:[] }; draft = null; renderCreate();
```

Contrôles : `#gridCount` affiche « N photo(s) · toute la bibliothèque » avec N = nombre de photos actives de `LIB` (tous genres) ; cliquer une ambiance réduit la liste (`filterByMoods`) ; cocher 2 ambiances affiche l'union ; « Principale » sur 3 photos → toast « Maximum 2 principales » ; « Modifier la description » sur une carte ouvre un textarea. Vérifier que `moodUnion(LIB, [ids sélectionnés])` donne les moods attendus dans la console.

- [ ] **Step 4: Commit**

```bash
git add poc-annonces-n8n/front/index.html
git commit -m "feat(poc-annonces-n8n): etape Inspirations (filtre multi-moods, principales/secondaires, mood en union)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 12: Étape 3 — Photos de l'annonce (première photo, suite, note globale)

**Files:**
- Modify: `poc-annonces-n8n/front/index.html`

**Interfaces:**
- Consumes : `renderPhotos(d)` (stub), `PLAN_LABELS`, `PLAN_ORDER`, `cleanErr`, `gradedUrl`, `imageUrl`, `origFigure`, `POST /job/suite`, `POST /job/plan`, `POST /job/garder`, `POST /job/feedback` (`cible: "global"`).
- Produces : `renderPhotos(d)`.

- [ ] **Step 1: HTML de `#stepPhotos`**

Remplacer `<section class="card hidden" id="stepPhotos"></section>` par :

```html
    <section class="card hidden" id="stepPhotos">
      <div class="row"><h2 class="grow">Photos de l'annonce</h2><span class="status" id="gStatus"></span></div>
      <p class="muted" id="gCost"></p>
      <div id="gError" class="bad"></div>
      <div id="firstBar" class="hidden review">
        <b>Cette première photo te convient ?</b>
        <div class="row" style="margin-top:8px">
          <button class="btn" id="nextBtn">Valider, générer les 2 autres (~0,16 $)</button>
          <span class="muted">Sinon utilise « Refaire cette photo » sous la photo (~0,08 $).</span>
        </div>
      </div>
      <div class="plans" id="plans"></div>
      <div id="finalBlock" class="hidden" style="margin-top:16px">
        <h3 id="gTitle"></h3>
        <p class="desc" id="gDesc"></p>
        <div class="row"><button class="btn ghost" id="gCopyTitle">Copier le titre</button><button class="btn ghost" id="gCopyDesc">Copier la description</button></div>
        <div class="card" style="margin-top:14px">
          <h2>Note finale</h2>
          <div class="row"><span id="globalRating"></span></div>
          <div class="chips" id="globalReasons"></div>
          <label>Commentaire</label>
          <textarea id="globalComment" placeholder="Qu'est-ce qui a marché, qu'est-ce qui a raté ?"></textarea>
          <div class="row" style="margin-top:8px"><button class="btn" id="globalSend">Envoyer la note finale</button><span class="muted" id="globalMsg"></span></div>
        </div>
      </div>
    </section>
```

- [ ] **Step 2: JS**

Remplacer le stub `function renderPhotos() {}` et supprimer l'ancienne `renderGallery` par :

```js
const planState = new Map();   // job_id|plan → { pastilles:Set, fb:string, raw:bool } : survit aux re-rendus
const inputPhotos = new Map(); // job_id → URL locale de la 1re photo d'entrée (fiches créées dans cette session)
let globalNote = null; let globalReasons = new Set();

function origFigure(url) {
  if (!url) return null;
  const img = h("img", { class: "orig", alt: "photo d'origine" });
  Promise.resolve(url).then(u => { img.src = u; }).catch(() => { img.alt = "photo d'origine indisponible"; });
  return h("figure", {}, img, h("figcaption", {}, "Photo d'origine"));
}

function renderPhotos() {
  const stateFor = plan => { const k = job.job_id + "|" + plan; if (!planState.has(k)) planState.set(k, { pastilles: new Set(), fb: "", raw: false }); return planState.get(k); };
  setStatus($("#gStatus"), job.statut);
  $("#gCost").textContent = "Coût : " + job.cout_total.toFixed(3) + " $ (texte " + job.cout_texte.toFixed(4) + " $, images " + job.cout_images.toFixed(3) + " $) · plafond " + (CONFIG ? CONFIG.plafond_usd : 1) + " $";
  $("#gError").textContent = job.statut === "erreur" ? job.erreur : "";
  const st = job.statut, first = st === "premiere_prete";
  const gallery = ["galerie_prete", "budget_depasse", "termine"].includes(st);
  $("#firstBar").classList.toggle("hidden", !(first && job.plans[0] && job.plans[0].statut === "pret"));
  $("#finalBlock").classList.toggle("hidden", !gallery);
  const box = $("#plans"); box.innerHTML = "";
  const origId = (job.input_photo_ids || [])[0];
  const origUrl = origId ? null : inputPhotos.get(job.job_id);
  const origFig = () => origId ? origFigure(imageUrl(origId)) : origFigure(origUrl);
  const canRegen = plan => (st === "galerie_prete" || st === "budget_depasse") || (first && plan === "porte_miroir");
  job.plans.forEach((p, idx) => {
    const card = h("div", { class: "card plan" });
    card.append(h("h3", {}, (idx + 1) + "/3 · " + (PLAN_LABELS[p.plan] || p.plan)));
    if (p.statut === "pret") {
      const img = h("img", { class: "shot", alt: "" });
      const ps = stateFor(p.plan); let raw = ps.raw;
      const show = () => (raw ? imageUrl(p.drive_file_id) : gradedUrl(p.drive_file_id)).then(u => { img.src = u; }).catch(() => { img.alt = "image indisponible"; });
      show();
      const right = h("figure", {}, img, h("figcaption", {}, raw ? "Générée (brute)" : "Générée (étalonnée)"));
      const rawBtn = h("button", { class: "btn ghost", onclick: () => { raw = ps.raw = !raw; rawBtn.textContent = raw ? "Voir étalonnée" : "Voir brut"; right.querySelector("figcaption").textContent = raw ? "Générée (brute)" : "Générée (étalonnée)"; show(); } }, raw ? "Voir étalonnée" : "Voir brut");
      const dl = h("a", { class: "muted", href: "#" }, "Télécharger");
      dl.addEventListener("click", async ev => {
        ev.preventDefault();
        try { const u = raw ? await imageUrl(p.drive_file_id) : await gradedUrl(p.drive_file_id);
          const a = h("a", { href: u, download: job.job_id + "_" + p.plan + (raw ? "_brut" : "") + ".jpg" }); document.body.append(a); a.click(); a.remove();
        } catch (e) { toast("Téléchargement impossible : " + e.message); }
      });
      card.append(h("div", { class: "pair" }, origFig(), right));
      card.append(h("div", { class: "bar" }, h("span", { class: "muted" }, p.fournisseur + " · " + (p.cout_plan || 0).toFixed(2) + " $"), rawBtn, dl));
      if (gallery) {
        const keep = h("input", { type: "checkbox" }); keep.checked = p.garde;
        keep.addEventListener("change", async () => { try { await api("POST", "/job/garder", { job_id: job.job_id, plan: p.plan, garde: keep.checked }); } catch (e) { toast(e.message); keep.checked = !keep.checked; } });
        card.append(h("div", { class: "bar" }, h("label", { style: "margin:0;color:var(--ink)" }, keep, " Garder")));
      }
    } else {
      const stage1 = job.plans[0].statut !== "pret" && job.plans.slice(1).every(x => x.statut === "en_attente");
      const msg = p.statut === "erreur" ? "Échec : " + cleanErr(p.erreur)
        : idx > 0 && stage1 ? "Après validation de la première photo"
        : st === "generation_en_cours" ? "En cours…" : "En attente";
      card.append(h("div", { class: "pair" }, origFig(), h("figure", {}, h("div", { class: "ph" }, msg))));
    }
    if (canRegen(p.plan) && (p.statut === "pret" || p.statut === "erreur")) {
      const pastilles = stateFor(p.plan).pastilles, pBox = h("div", { class: "chips" });
      for (const ps of (CONFIG && CONFIG.pastilles) || []) {
        const cb = h("input", { type: "checkbox" }); cb.checked = pastilles.has(ps.code);
        cb.addEventListener("change", () => cb.checked ? pastilles.add(ps.code) : pastilles.delete(ps.code));
        pBox.append(h("label", { class: "chip", style: "margin:0;color:var(--ink)", title: ps.fragment }, cb, " " + ps.code.replaceAll("_", " ")));
      }
      const fb = h("input", { type: "text", placeholder: "Consigne libre pour refaire (facultatif)", value: stateFor(p.plan).fb });
      fb.addEventListener("input", () => { stateFor(p.plan).fb = fb.value; });
      const force = st === "budget_depasse" ? h("input", { type: "checkbox" }) : null;
      const btn = h("button", { class: "btn ghost", onclick: async () => {
        btn.disabled = true;
        try { await api("POST", "/job/plan", { job_id: job.job_id, plan: p.plan, feedback: fb.value, pastilles: [...pastilles], force: !!(force && force.checked) }); await refreshJob(job.job_id); }
        catch (e) { toast(e.message); btn.disabled = false; }
      } }, "Refaire cette photo (~0,08 $)");
      card.append(h("div", { class: "muted", style: "margin-top:6px" }, "Ajustements pour la refaire :"), pBox, fb,
        h("div", { class: "bar" }, btn, force ? h("label", { style: "margin:0;color:var(--ink)" }, force, " dépasser le plafond") : null));
    }
    box.append(card);
  });
  if (gallery) {
    $("#gTitle").textContent = job.titre || ""; $("#gDesc").textContent = job.description || "";
    const fbk = job.feedback && job.feedback.global;
    $("#globalRating").innerHTML = "";
    const gUp = h("button", { class: "thumb-btn", onclick: () => { globalNote = "up"; renderGlobal(); } }, "👍");
    const gDown = h("button", { class: "thumb-btn", onclick: () => { globalNote = "down"; renderGlobal(); } }, "👎");
    $("#globalRating").append(gUp, gDown);
    if (fbk && !globalNote) { globalNote = fbk.note === "👍" ? "up" : "down"; $("#globalComment").value = fbk.commentaire || ""; globalReasons = new Set(fbk.raisons || []); }
    renderGlobal();
  }
}
function renderGlobal() {
  const [up, down] = $("#globalRating").children;
  if (up) { up.classList.toggle("on", globalNote === "up"); down.classList.toggle("on", globalNote === "down"); }
  const box = $("#globalReasons"); box.innerHTML = "";
  if (globalNote === "down" && CONFIG) for (const r of CONFIG.raisons.global || []) box.append(h("span", { class: "chip" + (globalReasons.has(r) ? " on" : ""), onclick: () => { globalReasons.has(r) ? globalReasons.delete(r) : globalReasons.add(r); renderGlobal(); } }, r.replaceAll("_", " ")));
}
$("#nextBtn").addEventListener("click", async () => {
  $("#nextBtn").disabled = true;
  try { await api("POST", "/job/suite", { job_id: job.job_id }); await refreshJob(job.job_id); }
  catch (e) { toast(e.message, 6000); }
  $("#nextBtn").disabled = false;
});
$("#gCopyTitle").addEventListener("click", () => copy(job.titre, "Titre"));
$("#gCopyDesc").addEventListener("click", () => copy(job.description, "Description"));
$("#globalSend").addEventListener("click", async () => {
  if (!globalNote) return toast("Choisis 👍 ou 👎");
  try {
    await api("POST", "/job/feedback", { job_id: job.job_id, cible: "global", note: globalNote, raisons: [...globalReasons], commentaire: $("#globalComment").value });
    $("#globalMsg").textContent = "Merci, annonce clôturée."; await refreshJob(job.job_id);
  } catch (e) { toast(e.message); }
});
```

Dans le handler de création (`#createBtn`), la ligne `inputPhotos.set(r.job_id, URL.createObjectURL(files[0]));` reste ; supprimer les anciennes déclarations `const planState`, `const inputPhotos`, `let globalNote`, `let globalReasons`, `origFigure` situées plus haut/bas pour éviter les doublons. Supprimer maintenant les fonctions mortes de l'ancien flux (`ratingWidget`, `renderFiche`, `renderStyleGrid`, `renderReview`, `renderGallery`, `preselect`, `pickMood`, `useAsInspi`, `syncGarment`, `inspiInfo`) si elles subsistent.

- [ ] **Step 3: Vérifier (aucun coût)**

Console du navigateur intégré, avec `LIB` chargée et sans réseau :

```js
const pl = (plan, statut, extra={}) => Object.assign({ plan, statut, tentative:1, drive_file_id:"", cout_plan:0.08, fournisseur:"fal", garde:true, erreur:"" }, extra);
const base = { job_id:"x", titre:"T", description:"D", cout_total:0.08, cout_texte:0.0002, cout_images:0.08, input_photo_ids:[], feedback:{} };
job = { ...base, statut:"premiere_prete", plans:[pl("porte_miroir","pret"), pl("cintre","en_attente"), pl("detail","en_attente")] }; draft=null; renderCreate();
```

Contrôles : `#firstBar` visible ; carte 1 avec « Refaire cette photo » ; cartes 2 et 3 avec « Après validation de la première photo » et **sans** bouton refaire ; `#finalBlock` masqué. Puis `job = { ...base, statut:"galerie_prete", plans:[pl("porte_miroir","pret"),pl("cintre","pret"),pl("detail","erreur",{erreur:"Photos : délai dépassé"})] }; renderCreate();` : `#firstBar` masqué, `#finalBlock` visible, la carte 3 affiche `Échec : délai dépassé` avec le bouton refaire ; aucun bouton 👍/👎 par photo. `read_console_messages onlyErrors` : aucune erreur.

```bash
cd poc-annonces-n8n && node --test scripts/test_front_logic.mjs
```

Expected : `pass`.

- [ ] **Step 4: Commit**

```bash
git add poc-annonces-n8n/front/index.html
git commit -m "feat(poc-annonces-n8n): etape Photos (premiere photo puis suite, note globale seule)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 13: Historique (consultation)

**Files:**
- Modify: `poc-annonces-n8n/front/index.html`

**Interfaces:**
- Consumes : `GET /jobs` (Task 5), `summarize` (Task 8), `GET /job-status`, `gradedUrl`, `lazyImg`, `STATUS_LABELS`, `PLAN_LABELS`, `cleanErr`, `copy`.
- Produces : `loadHistory()`, `renderHistory()`.

- [ ] **Step 1: JS (le conteneur `#tab-historique` est vide, on le remplit par JS)**

Ajouter avant `// ---------- réglages & démarrage ----------` (ou l'ancre équivalente) :

```js
// ---------- historique (consultation seule) ----------
let HIST = null, histDays = 30;
async function loadHistory() {
  try { HIST = (await api("GET", "/jobs")).jobs; } catch (e) { return toast(e.message); }
  renderHistory();
}
const money = v => Number(v || 0).toFixed(3) + " $";
function renderHistory() {
  const root = $("#tab-historique"); root.innerHTML = "";
  if (!HIST) return;
  const s = summarize(HIST, histDays, Date.now());
  const sel = h("select", { style: "width:auto" }, [[7, "7 derniers jours"], [30, "30 derniers jours"], [0, "Tout"]].map(([v, l]) => h("option", { value: v, ...(v === histDays ? { selected: "" } : {}) }, l)));
  sel.addEventListener("change", () => { histDays = Number(sel.value); renderHistory(); });
  const stat = (k, v) => h("div", {}, h("div", { class: "k" }, k), h("div", { class: "v" }, v));
  root.append(h("section", { class: "card" },
    h("div", { class: "row" }, h("h2", { class: "grow" }, "Historique"), sel),
    h("div", { class: "hist-totals" }, stat("Annonces", String(s.fiches)), stat("Images générées", String(s.images) + (s.regenerations ? " (dont " + s.regenerations + " refaites)" : "")),
      stat("Coût du texte", money(s.cout_texte)), stat("Coût des images", money(s.cout_images)), stat("Coût total", money(s.cout_total)),
      stat("Moyenne par annonce", s.fiches ? money(s.cout_total / s.fiches) : "—")),
    h("p", { class: "muted", style: "margin-top:8px" }, "Coût des images = unités facturées par Fal × tarif de config_image ; coût du texte = retour réel d'OpenRouter.")));
  if (!s.list.length) root.append(h("p", { class: "muted" }, "Aucune annonce sur cette période."));
  for (const j of s.list) {
    const detail = h("div", { class: "hidden", style: "margin-top:12px;grid-column:1 / -1" });
    const row = h("div", { class: "card" });
    const head = h("div", { class: "hist-row" },
      j.cover_file_id ? lazyImg(j.cover_file_id) : h("div", { class: "ph", style: "width:64px;height:84px;aspect-ratio:auto;font-size:11px" }, "—"),
      h("div", {}, h("strong", {}, j.titre || "(annonce sans titre)"),
        h("div", { class: "muted" }, new Date(j.created_at).toLocaleString("fr-FR") + " · " + j.user + " · " + [j.genre, j.type_vetement].filter(Boolean).join(" ")),
        h("div", { class: "muted" }, (STATUS_LABELS[j.statut] || j.statut) + " · " + j.nb_images + " image(s)" + (j.nb_regenerations ? " dont " + j.nb_regenerations + " refaite(s)" : "") + (j.note_globale ? " · " + j.note_globale : ""))),
      h("div", { style: "text-align:right" }, h("div", { class: "v", style: "font-size:16px;font-weight:650" }, money(j.cout_total)), h("div", { class: "muted" }, "texte " + money(j.cout_texte) + " · images " + money(j.cout_images))));
    let loaded = false;
    head.addEventListener("click", async () => {
      detail.classList.toggle("hidden");
      if (loaded || detail.classList.contains("hidden")) return; loaded = true;
      detail.append(h("span", { class: "muted" }, "Chargement…"));
      try {
        const d = await api("GET", "/job-status?id=" + encodeURIComponent(j.job_id));
        detail.innerHTML = "";
        const shots = h("div", { class: "plans", style: "grid-template-columns:repeat(auto-fit,minmax(200px,1fr))" });
        for (const p of d.plans) {
          const fig = h("figure", { style: "margin:0" });
          if (p.statut === "pret") { const img = h("img", { class: "shot", alt: "" }); gradedUrl(p.drive_file_id).then(u => { img.src = u; }).catch(() => { img.alt = "image indisponible"; }); fig.append(img); }
          else fig.append(h("div", { class: "ph" }, p.statut === "erreur" ? "Échec : " + cleanErr(p.erreur) : "Pas générée"));
          fig.append(h("figcaption", { class: "muted" }, (PLAN_LABELS[p.plan] || p.plan) + (p.statut === "pret" ? " · " + p.fournisseur + " · " + money(p.cout_plan) + (p.tentatives_total > 1 ? " · " + p.tentatives_total + " tentatives" : "") : "")));
          shots.append(fig);
        }
        detail.append(h("h3", {}, d.titre || ""), h("p", { class: "desc" }, d.description || ""),
          h("div", { class: "row" }, h("button", { class: "btn ghost", onclick: () => copy(d.titre, "Titre") }, "Copier le titre"), h("button", { class: "btn ghost", onclick: () => copy(d.description, "Description") }, "Copier la description")),
          d.erreur ? h("p", { class: "bad" }, d.erreur) : null, shots);
      } catch (e) { detail.innerHTML = ""; detail.append(h("span", { class: "bad" }, e.message)); loaded = false; }
    });
    row.append(head, detail); root.append(row);
  }
}
```

- [ ] **Step 2: Vérifier**

```bash
cd poc-annonces-n8n && node --test scripts/test_front_logic.mjs
```

Dans le navigateur intégré, onglet Historique : totaux affichés ; « Tout » liste toutes les fiches (dont celles de test) ; le total « Coût total » de l'entête = somme des lignes (contrôle : `HIST.reduce((a,j)=>a+j.cout_total,0)` en console, à 0,001 $ près, avec « Tout ») ; clic sur `muftpawvta7x` : texte + 3 vignettes étalonnées, coût ≈ 0,240 $ ; changer la période à « 7 derniers jours » réduit le nombre de fiches ; aucune action de modification (pas de bouton de régénération).

- [ ] **Step 3: Commit**

```bash
git add poc-annonces-n8n/front/index.html
git commit -m "feat(poc-annonces-n8n): historique en consultation (totaux, couts, detail d'une annonce)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 14: Réglages — Bibliothèque avec description modifiable et vérification finale des sections

**Files:**
- Modify: `poc-annonces-n8n/front/index.html`

**Interfaces:**
- Consumes : `POST /library/update` avec `description_en` (Task 4), `renderLibrary`.

- [ ] **Step 1: Description anglaise modifiable dans la bibliothèque**

Dans `renderLibrary()` (Réglages > Bibliothèque), remplacer la ligne qui construit `card.append(lazyImg(…), …)` par la même liste d'éléments plus, avant le `label` « active », ce bloc :

```js
    const descBox = h("div", { class: "hidden" });
    const ta = h("textarea", {}); ta.value = it.description_en || "";
    descBox.append(ta, h("button", { class: "btn ghost", style: "margin-top:4px", onclick: async () => {
      try { const r = await api("POST", "/library/update", { drive_file_id: it.drive_file_id, description_en: ta.value }); it.description_en = r.description_en; toast("Description enregistrée"); } catch (e) { toast(e.message); }
    } }, "Enregistrer"));
```

et ajouter dans `card.append(…)` : `h("button", { class: "linkbtn", onclick: () => descBox.classList.toggle("hidden") }, "Modifier la description"), descBox,`. Le champ `title: it.description` des tags reste.

- [ ] **Step 2: Vérifier les sections**

Navigateur intégré, Réglages : (a) Connexion — enregistrer une URL/un secret identiques ne casse rien (toast « Connexion enregistrée ») ; (b) Profil — le texte de l'utilisateur sélectionné se charge, le compteur de caractères s'affiche, changer d'utilisateur recharge le profil ; (c) Bibliothèque — filtres et grille fonctionnent ; modifier la description d'une photo de test (photo inactive du README) puis recharger : la nouvelle valeur persiste (remettre l'ancienne) ; (d) Prompts — la liste se charge, « Voir le texte » affiche le prompt, aucune activation lancée. `read_console_messages onlyErrors` : aucune erreur.

- [ ] **Step 3: Commit**

```bash
git add poc-annonces-n8n/front/index.html
git commit -m "feat(poc-annonces-n8n): reglages editables (description anglaise de la bibliotheque)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 15: Nettoyage du front

**Files:**
- Modify: `poc-annonces-n8n/front/index.html`

- [ ] **Step 1: Repérer le code mort**

```bash
cd poc-annonces-n8n && grep -n "renderGallery\|renderStyleGrid\|renderReview\|ratingWidget\|showTab(\"galerie\|tab-galerie\|tab-fiche\|tab-profil\|tab-prompts\|tab-biblio\|jobCard\|moodSelect\|photoSansMiroir\|reviewPanel\|allTypes\|openBtn\|settingsBtn\|#settings\|fiche" front/index.html
```

Expected : aucune occurrence des identifiants supprimés (`renderGallery`, `renderStyleGrid`, `renderReview`, `ratingWidget`, `tab-galerie`, `tab-fiche`, `jobCard`, `moodSelect`, `photoSansMiroir`, `reviewPanel`, `allTypes`, `openBtn`, `settingsBtn`, `#settings`). Supprimer tout ce qui reste (fonctions, écouteurs, CSS `.review ol`, `.review li` si inutilisés). Remplacer les mots « fiche » par « annonce » dans les textes affichés à l'utilisateur (l'identifiant technique `job_id` et les noms d'endpoints ne changent pas).

- [ ] **Step 2: Vérifier**

```bash
cd poc-annonces-n8n && node --test scripts/test_front_logic.mjs && grep -c "renderGallery" front/index.html
```

Expected : tests `pass` et `0`. Dans le navigateur intégré : les 3 onglets s'ouvrent, `read_console_messages onlyErrors` vide.

- [ ] **Step 3: Commit**

```bash
git add poc-annonces-n8n/front/index.html
git commit -m "refactor(poc-annonces-n8n): retrait du code de l'ancien flux (relecture, galerie, notes par photo)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

# LOT 3 — Vérification de bout en bout

### Task 16: Parcours complet réel (une seule dépense)

**Files:**
- Modify: `poc-annonces-n8n/README.md`

- [ ] **Step 1: Annonce (coût ≈ 0,0002 $)**

Dans le navigateur intégré (`http://localhost:8765`, onglet Créer), remplir le formulaire avec 3 photos de test (`poc-annonces/` contient les entrées du jeu de test humain), genre `femme`, type `t-shirt`, marque, taille, prix, état ; « Créer l'annonce ». Contrôles : le stepper marque l'étape 1 ; le journal affiche `Lecture des photos…` puis `Rédaction de l'annonce…` (3 s plus tard) puis `Annonce prête ✓` ; le titre et la description s'affichent ; le bouton « Modifier la description du vêtement pour les photos » révèle le texte anglais ; « Mettre à jour le texte » avec un message relance la génération.

- [ ] **Step 2: Inspirations (aucun coût)**

« Choisir les inspirations → » : le journal affiche `Recherche des inspirations dans la bibliothèque…` puis `Inspirations proposées : à toi de choisir ✓` ; l'étape 2 s'affiche avec la bibliothèque entière ; cocher une ambiance filtre ; choisir 2 principales et 2 secondaires ; ouvrir « Modifier la description du mannequin ».

- [ ] **Step 3: Première photo (≈ 0,08 $)**

« Générer la première photo » : journal `Génération de la photo portée (1/3)…` puis `Photo « Porté » prête (1/3) ✓ 0.08 $` puis `Première photo prête : à toi de la valider.` ; le statut est `premiere_prete` ; seule la photo portée est affichée ; les deux autres indiquent « Après validation de la première photo ». Vérifier côté n8n : 1 seule ligne `shots` pour ce job ; `mood` du job = union des moods des 4 inspirations :

```bash
curl -s -H "X-VFN-Secret: $VFN_SECRET" "https://178-105-102-54.sslip.io/webhook/vfn/job-status?id=<job_id>" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["statut"], d["mood"], [(p["plan"],p["statut"]) for p in d["plans"]])'
```

Expected : `premiere_prete <moods séparés par des virgules> [('porte_miroir','pret'),('cintre','en_attente'),('detail','en_attente')]`.

- [ ] **Step 4: Contrôles du garde-fou (aucun coût)**

```bash
# cintre refusé tant que la première photo n'est pas validée : 409
curl -s -w " %{http_code}\n" -X POST -H "X-VFN-Secret: $VFN_SECRET" -H "Content-Type: application/json" -d '{"job_id":"<job_id>","plan":"cintre"}' https://178-105-102-54.sslip.io/webhook/vfn/job/plan
```

Expected : `409`.

- [ ] **Step 5: Suite (≈ 0,16 $)**

« Valider, générer les 2 autres » : journal `Génération des photos 2/3 et 3/3…`, puis une ligne `Photo « Sur cintre » prête (2/3) ✓` et une `Photo « Détail » prête (3/3) ✓`, puis `Les 3 photos sont prêtes ✓ (coût total ≈ 0.24 $)`. La note finale apparaît ; envoyer 👍 avec un commentaire : statut `termine`.

- [ ] **Step 6: Historique**

Onglet Historique, période « Tout » : la nouvelle annonce est en tête avec une miniature de la photo portée, 3 images, coût ≈ 0,240 $ (texte ≈ 0,0002 $) ; le détail affiche le texte et les 3 photos. Comparer avec `GET /jobs` (`nb_images = 3`, `cout_total` identique à `job-status`).

- [ ] **Step 7: Erreurs lisibles**

Insérer (outil `add_data_table_rows`) une fiche `test_erreur2` en `texte_en_cours` avec un `drive_input_folder_id` inexistant, l'ouvrir dans le front (`store.set("job","test_erreur2"); start()`), lancer le sous-workflow texte comme en Task 6 Step 1 : le journal doit afficher `⚠ Texte : …` en rouge, le bouton « Réessayer » apparaître à l'étape 1. Supprimer ensuite la ligne depuis l'UI n8n.

- [ ] **Step 8: Mettre à jour le README et commit**

Ajouter à la fin de la section « Référence des workflows n8n » un paragraphe `### Parcours, historique et erreurs (2026-09-25)` : nouveaux workflows, statut `premiere_prete`, paramètre `plans`, `/job/suite`, `/jobs`, comportement d'erreur (Texte/Style immédiat, Photos après délai), tests exécutés (`node --test`, parcours réel, coût réel constaté), fiches de test créées à supprimer (`test_erreur*` et l'annonce du Step 1 si l'utilisateur le souhaite), et la formule du coût Fal (`unités facturées × config_image.fal_cost_per_unit_usd`, à comparer au dashboard Fal).

```bash
git add poc-annonces-n8n/README.md
git commit -m "docs(poc-annonces-n8n): parcours guide, historique et erreurs lisibles (verification de bout en bout)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Auto-revue (couverture des décisions)

- Parcours Annonce → Inspirations → Photos, 3 entrées : Task 9-12.
- Journal grisé, messages réels (photos) et temporisé (texte) : Task 8 (`journalLines`), Task 9 (`armTextTimer`).
- Anglais masqué + boutons « Modifier la description » (vêtement Task 10, mannequin et inspirations Task 11, bibliothèque Task 14) ; `description_en` éditable côté n8n : Task 4.
- Filtre multi-moods sur toute la bibliothèque, principales/secondaires, mood en union sans LLM : Task 8, 11 ; ligne « Overall mood » omise si vide : Task 4.
- Première photo puis suite : Task 2 (statut, `plans`), Task 3 (`/job/suite`), Task 12 (UI). Refaire la 1re photo : Task 2 Step 4, Task 12.
- Feedback global seulement + 👍 global pour les exemples : Task 4 Step 2, Task 12.
- Historique consultation avec coûts, tous users, tests inclus : Task 5, 13.
- Réglages éditables : Task 9, 14.
- Workflow d'erreur + surveillance : Task 6 ; erreurs affichées : `journalLines`, `renderText`, `renderInspi`, `renderPhotos`.
- Cohérence des noms : `renderText/renderInspi/renderPhotos(d)`, `stepOf`, `moodUnion`, `filterByMoods`, `journalLines`, `summarize`, `cleanErr`, `PLAN_LABELS`, `PLAN_ORDER`, statut `premiere_prete`, champ `plans` (liste côté front, `plans_csv` en interne), endpoints `/job/suite`, `/jobs`.
- Limites connues : le déclencheur d'erreur de n8n ne fournit pas le `job_id` (ciblage par statut, sinon surveillance) ; l'Error Trigger peut ne pas se déclencher pour un sous-workflow (Task 6 Step 4 le vérifie, la surveillance est le filet) ; le polling `job-status` garde son listage Drive (choix de l'utilisateur) ; les fiches de test restent dans l'historique.

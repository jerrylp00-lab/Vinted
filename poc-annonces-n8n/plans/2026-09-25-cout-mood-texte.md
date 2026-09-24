# Coût, mood choisi, image → texte — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ramener le coût d'une fiche sous 0,20 $ (3 images, aucun retry, aucun appel LLM de sélection), laisser l'utilisateur choisir mood / inspirations / mannequin, et remplacer les références image par des descriptions anglaises longues sauf 2 inspirations.

**Architecture:** Modifications des workflows n8n existants (aucun nouveau service) : nouvelles versions de prompts dans `prompts`, nouvelles colonnes dans `library` et `jobs`, sélection de style sans LLM, génération à 3 plans sans check ni retry, front HTML adapté. Spec : `specs/2026-09-25-cout-mood-texte-design.md`. Vocabulaire : `poc-annonces/CONTEXT.md` (Plan, Brief, Mood, decor_refs).

**Tech Stack:** n8n (instance `https://178-105-102-54.sslip.io`, outils MCP `mcp__n8n-mcp__*`), Data Tables n8n, Fal.ai (Nano Banana 2) + repli OpenRouter, OpenRouter `google/gemini-2.5-flash-lite`, front `front/index.html` (JS natif), `curl`.

## Global Constraints

- Plans : exactement `porte_miroir`, `cintre`, `detail`, dans cet ordre. `a_plat` n'existe plus nulle part.
- Aucun retry automatique d'image, aucun check de fidélité automatique.
- Inspirations : 2 maximum en vision (`jobs.decor_refs`), 3 maximum en texte (`jobs.inspi_texte`).
- Toute modification de prompt = **nouvelle ligne** dans `prompts` (`version` suivante), activée à la main, l'ancienne version restant disponible pour le retour arrière. Les jetons `{n}`, `{profil}`, `{exemples}` existants doivent être conservés là où ils existent.
- Descriptions de bibliothèque, `garment_en`, mannequin et briefs : en anglais. Interface, titre et description Vinted : en français.
- Le mannequin n'est jamais envoyé en image. Le visage n'est jamais visible.
- Plafond de coût par fiche inchangé (1 $, `config_plafond`).
- Secrets : header `X-VFN-Secret` sur chaque webhook ; jamais de clé ni de secret dans le dépôt.
- Base des webhooks pour les commandes ci-dessous : `BASE=https://178-105-102-54.sslip.io/webhook/vfn` et `VFN_SECRET` dans l'environnement du shell.
- Ne pas lancer de génération d'image réelle hors des tâches qui le demandent (coût) ; utiliser `test_workflow` avec pin data ailleurs.

## Structure des fichiers

- Modifier : `poc-annonces-n8n/front/index.html` (formulaire, choix du style, écran « ce que l'IA va voir », galerie).
- Modifier : `poc-annonces-n8n/README.md` (section « Étape 9 » à la fin de chaque tâche terminée).
- Créer : `poc-annonces-n8n/scripts/measure_cost.sh` (lit `cout_texte`, `cout_images`, `cout_total` d'une fiche).
- Modifier dans n8n (IDs du README) : `k7j9FcAjqQKLYCj1` (indexation), `5erMviLZ0qLPtd1E` (créer fiche), `gdGJLLnGtW79Jeol` (texte), `bRdAbgJiiGKwNyvP` (affiner), `FI9HyhPdvbATuSqw` + `ao81dPakf9IqTIyr` (style), `z1SY3ZkptHVSd4al` (valider), `9Y0O9Z4MO9wVM0xB` (générer les plans), `HKMVyeJJQTSoBN6X` (générer un plan), `pGvWMH08Go4yGJYp` (tentative image), `MIeRXvNz9a4cwKIo` (régénérer), `DgoKnyLMpuLqabFh` (feedback), `3EkEko4Qo2ofd7LK` (statut), `fES1vA8Ak6Vz9N6K` (config front), `a6h3K0SfbhFY4cBp` (upload inspirations), `LtGZGU42Lkx2ip3u` (journal).
- Créer dans n8n : `VFN — Migrer les descriptions (unique)`.

Méthode pour toute édition de workflow : `get_sdk_reference` et `get_workflow_best_practices`, puis `get_workflow_details` du workflow visé, modification ciblée avec `update_workflow`, vérification avec `validate_workflow`, puis `test_workflow` (pin data) ou appel réel indiqué. Ne jamais réécrire un workflow de zéro : les nœuds non cités restent tels quels.

---

### Task 0: Référence de coût et de rendu (avant tout changement)

**Files:**
- Create: `poc-annonces-n8n/scripts/measure_cost.sh`

**Interfaces:**
- Produces: `scripts/measure_cost.sh <job_id>` affiche `cout_texte cout_images cout_total` ; la référence chiffrée avant/après pour la Task 10.

- [ ] **Step 1: Écrire le script de mesure**

```bash
#!/usr/bin/env bash
# Usage : VFN_SECRET=... ./scripts/measure_cost.sh <job_id>
set -euo pipefail
BASE="${VFN_BASE:-https://178-105-102-54.sslip.io/webhook/vfn}"
curl -sf -H "X-VFN-Secret: ${VFN_SECRET:?}" "$BASE/job-status?id=$1" \
  | python3 -c 'import json,sys; j=json.load(sys.stdin); print({k: j.get(k) for k in ("statut","cout_texte","cout_images","cout_total")}); print([(p["plan"], p.get("cout"), p.get("fournisseur")) for p in j.get("plans",[])])'
```

- [ ] **Step 2: Rendre exécutable et mesurer la fiche de référence**

Run: `chmod +x poc-annonces-n8n/scripts/measure_cost.sh && VFN_SECRET=... poc-annonces-n8n/scripts/measure_cost.sh mufe74xl35gs`
Expected: `cout_total` autour de 0.56 (README, étape 4). Noter le chiffre exact dans le README section « Étape 9 — référence avant ».

- [ ] **Step 3: Figer le jeu de test**

Demander à l'utilisateur les photos du maillot PSG (mêmes que la capture de la session) et les déposer dans `poc-annonces/Test_humain/PSG/` (dossier non versionné). Ce sont les entrées des Tasks 5 à 10.

- [ ] **Step 4: Commit**

```bash
git add poc-annonces-n8n/scripts/measure_cost.sh poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: script de mesure de coût, référence avant refonte"
```

---

### Task 1: Colonnes Data Tables

**Files:**
- Modifier dans n8n : tables `library` (`szOLa2GMVs8D2AHi`) et `jobs` (`vVa4oB747ymKwzw8`)

**Interfaces:**
- Produces : `library.description_en` (string), `library.utilisations` (number) ; `jobs.marque`, `jobs.taille`, `jobs.mesures`, `jobs.etat`, `jobs.prix`, `jobs.texte_visible`, `jobs.garment_en`, `jobs.mannequin_desc`, `jobs.inspi_texte` (toutes string ; `inspi_texte` contient du JSON `[{file_id, nom_fichier, description_en}]`).

- [ ] **Step 1: Ajouter les colonnes** avec `add_data_table_column` (type `string`, sauf `utilisations` de type `number`) sur chaque table.

- [ ] **Step 2: Vérifier**

Run: `search_data_tables` (query `library` puis `jobs`)
Expected: les 2 colonnes de `library` et les 9 de `jobs` sont listées.

- [ ] **Step 3: Initialiser `utilisations` à 0** sur les 23 lignes existantes : fait par la migration de la Task 3 (ne rien faire ici).

- [ ] **Step 4: Commit** (README : ligne « Étape 9 — colonnes ajoutées »)

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, colonnes library/jobs pour mood choisi et texte anglais"
```

---

### Task 2: Nouvelles versions de prompts (inactives)

**Files:**
- Modifier dans n8n : table `prompts` (`vqb7uMK180X3MbKm`), via `add_data_table_rows`

**Interfaces:**
- Produces : lignes `prompts` avec `actif = false` : `brief_commun` v2, `brief_ref_mannequin` v2, `config_mannequins` v2, `brief_plan_porte_sans_miroir` v1, `brief_garment_en` v1, `brief_inspi_texte` v1, `config_pastilles` v1, `texte_fiche` v3, `indexation_photo` v2, `config_image` v2. Leur activation se fait dans la tâche qui les consomme.

- [ ] **Step 1: Lire les versions actives** avec `GET $BASE/prompts` (ou `search_data_tables` puis lecture des lignes). Copier le texte actuel de `texte_fiche` (v2), `indexation_photo` (v1), `brief_ref_mannequin` (v1), `config_image` (v1).

- [ ] **Step 2: Ajouter les lignes suivantes** (`notes` = « 2026-09-25 refonte coût/mood »), `actif = false`.

`brief_commun` v2 :
```
Act as a photographer specialised in Parisian 'effortless chic' and UGC (user generated content) aesthetics for a second-hand fashion seller. Realistic photo, as taken with a recent smartphone or a 35mm film camera: natural light, soft shadows, slight grain, muted and slightly desaturated colours, gentle film colour grade, no oversaturation, no HDR, no glossy commercial look. No 3D, no CGI, no sterile studio background. The garment must look really worn and lived-in: natural non-rigid drape, slightly creased, not freshly ironed, and lit by the SAME light as the room (same colour temperature, same shadows and reflections) so that garment and environment look photographed together. Reproduce the garment EXACTLY as described and shown: colour, print, text, trims, cut and fabric. Invent no detail. Generate exactly ONE image. Do not add any text or watermark.
```

`brief_plan_porte_sans_miroir` v1 :
```
The garment worn by a person of average build, photographed as a casual smartphone photo taken by a friend, framed from the neck to the hips so that the face is not visible. The garment faces the camera and is fully readable: print, text and logo read left to right, never mirrored. Background: chic vintage Parisian apartment, wooden parquet floor, natural light from a window.
```

`brief_garment_en` v1 :
```
Garment description (source of truth, in addition to the attached photos): {garment_en}
```

`brief_inspi_texte` v1 :
```
Additional style references, described in words only (no image): use them as extra inspiration for mood, light, palette and decor, never copy them literally.
{liste}
```

`brief_ref_mannequin` v2 :
```
The person wearing the garment: {mannequin_desc} The face must never be visible.
```

`config_mannequins` v2 (valeurs de départ, à affiner par l'utilisateur) :
```json
{"Femme": "A woman in her late twenties, average build (EU size 38), about 1m68, shoulder-length dark brown hair, relaxed natural posture, casual everyday style.", "Homme": "A man in his late twenties, average build (EU size M), about 1m78, short dark curly hair, relaxed natural posture, casual everyday style."}
```

`config_pastilles` v1 :
```json
{"trop_sombre": "Make the image brighter, with more natural daylight.", "trop_sature": "Reduce colour saturation: more muted and natural colours.", "couleur_fausse": "The garment colour is wrong: match exactly the colour of the reference photos.", "vetement_deforme": "The garment shape is distorted: restore the exact cut, proportions and details of the reference photos.", "trop_mis_en_scene": "Make the scene more casual and spontaneous, less staged, like a quick everyday photo.", "piece_trop_rangee": "Make the room lived-in and slightly messy, with a few everyday objects, less tidy."}
```

`texte_fiche` v3 (conserver `{profil}` et `{exemples}`) :
```
You are an experienced Vinted seller writing honest, simple listings. From the photos of ONE garment, return a JSON object with:
- "description": 2 to 3 short, factual sentences in French (garment type, colour, cut, one or two visible qualities, visible condition). No superlatives, no invention. The seller's form data (brand, size, measurements, condition, price) is added separately by the app: never state brand, size or measurements yourself.
- "garment_en": a precise description in English, 60 to 100 words, of the garment only: main colour and shades, print or graphics, any text or logo exactly as written, neckline, sleeves, cut and length, fabric look, trims, buttons or seams, notable details. It is used to brief an image model: no opinion, no marketing wording.
{profil}
{exemples}
Respond only with a JSON object matching the requested schema.
```

`indexation_photo` v2 : copier le texte de la v1 et **remplacer uniquement** l'instruction de description par :
```
"description": in English, 120 to 180 words, describing only the visual style of the reference photo: the setting (indoor/outdoor, walls, floor, furniture, vegetation), the light (natural or artificial, soft or hard, direction, time of day), the palette, the materials and textures, the composition and framing (wide or tight, angle, depth of field), and the overall atmosphere. Do not describe the garment or the identity of any person.
```

`config_image` v2 : copier le JSON de la v1 sans changement pour l'instant (la résolution et le coût sont réglés en Task 7).

- [ ] **Step 3: Vérifier**

Run: `curl -s -H "X-VFN-Secret: $VFN_SECRET" $BASE/prompts | python3 -c 'import json,sys; [print(p["nom"],p["version"],p["actif"]) for p in json.load(sys.stdin)["prompts"] if p["version"]>=2 or p["nom"] in ("brief_garment_en","brief_inspi_texte","config_pastilles","brief_plan_porte_sans_miroir")]'`
Expected: chaque prompt listé avec `actif False` sauf les versions précédentes toujours `True`. (Si le format de la réponse diffère, adapter le filtre au JSON réel.)

- [ ] **Step 4: Commit** (README : liste des prompts ajoutés)

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, nouvelles versions de prompts (inactives)"
```

---

### Task 3: Indexation en anglais + migration des descriptions existantes

**Files:**
- Modifier dans n8n : `VFN — Indexation bibliothèque` (`k7j9FcAjqQKLYCj1`)
- Créer dans n8n : `VFN — Migrer les descriptions (unique)`

**Interfaces:**
- Consumes : `prompts.indexation_photo` v2 (Task 2), colonnes `library.description_en`, `library.utilisations` (Task 1).
- Produces : toute nouvelle ligne `library` reçoit `description_en` (anglais, 120-180 mots) et `utilisations = 0` ; les 23 lignes existantes reçoivent `description_en` et `utilisations = 0`.

- [ ] **Step 1: Activer `indexation_photo` v2**

Run: `curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d '{"nom":"indexation_photo","version":2}' $BASE/prompts/activer`
Expected: version 2 active, version 1 inactive.

- [ ] **Step 2: Adapter le workflow d'indexation**

Dans le workflow `k7j9FcAjqQKLYCj1`, dans le nœud (Code) qui lit la réponse du LLM et construit la ligne à insérer : écrire la `description` renvoyée dans **`description_en`** (et laisser `description` vide pour les nouvelles photos), ajouter `utilisations: 0`. Dans le nœud d'insertion Data Table, ajouter les deux colonnes au mapping. Le schéma JSON de sortie du LLM garde les mêmes clés (`description`, `tags`, `moods`).

- [ ] **Step 2b: Le dépôt d'une photo renvoie son identifiant**

Dans `a6h3K0SfbhFY4cBp` (upload), vérifier que la réponse contient les `drive_file_id` créés (le front s'en sert en Task 9). S'ils manquent, les ajouter à la réponse.

- [ ] **Step 3: Créer le workflow de migration** (déclencheur manuel), avec ces nœuds :
  1. Data Table `get` sur `library`, filtre : `description_en` est vide.
  2. Code (`runOnceForEachItem`) qui construit le corps de requête :

```js
const r = $json;
const body = {
  model: 'google/gemini-2.5-flash-lite',
  messages: [{ role: 'user', content:
    'Translate into English and expand to 120-180 words this description of the visual style of a reference photo (setting, light, palette, materials, composition, atmosphere). Keep every fact, add no invention, do not describe the garment or any person identity. Reply with the text only.\n\n' + (r.description || '') }],
  usage: { include: true }
};
return { json: { row_id: r.id, body } };
```
  3. HTTP Request `POST https://openrouter.ai/api/v1/chat/completions` (credential `openRouterApi`, corps `{{ $json.body }}`).
  4. Data Table `update` sur `library` : filtre `id = {{ $('Code').item.json.row_id }}`, colonnes `description_en = {{ $json.choices[0].message.content.trim() }}`, `utilisations = 0`.

- [ ] **Step 4: Tester sur une ligne puis sur tout**

Run : exécuter le workflow (`execute_workflow`), puis `curl -s -H "X-VFN-Secret: $VFN_SECRET" $BASE/library | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sum(1 for r in d.get("photos", d) if r.get("description_en")), "sur", len(d.get("photos", d)))'`
Expected: `23 sur 23`. Coût total attendu : de l'ordre de 0,01 $.

- [ ] **Step 5: Tester l'indexation d'une nouvelle photo**

Run : ajouter une photo via `POST $BASE/library/upload` (multipart : `genre`, `type_vetement`, `photo0`). Lire la ligne créée : `description_en` en anglais, 120-180 mots, 1 à 3 moods valides.

- [ ] **Step 6: Commit** (README : étape 9, indexation + migration)

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, indexation en anglais et migration des descriptions"
```

---

### Task 4: Création de fiche avec le formulaire

**Files:**
- Modifier dans n8n : `VFN — Créer une fiche (webhook)` (`5erMviLZ0qLPtd1E`), `VFN — Lire une fiche (statut)` (`3EkEko4Qo2ofd7LK`), `VFN — Configuration pour le front` (`fES1vA8Ak6Vz9N6K`)

**Interfaces:**
- Consumes : colonnes `jobs` (Task 1).
- Produces : `POST /job` accepte en plus dans le multipart `marque`, `taille`, `mesures`, `etat`, `prix`, `texte_visible` (`true`/`false`) et les enregistre dans `jobs` ; `GET /job-status` renvoie en plus `marque`, `taille`, `mesures`, `etat`, `prix`, `texte_visible`, `garment_en`, `mannequin_desc`, `inspi_texte` (JSON déjà parsé en tableau) ; `GET /config` renvoie `plans: ["porte_miroir","cintre","detail"]` et `pastilles: [{code, fragment}]` lues dans `config_pastilles`.

- [ ] **Step 1: Ajouter les champs à la création**

Dans le nœud qui écrit la ligne `jobs` du workflow `5erMviLZ0qLPtd1E`, mapper `marque`, `taille`, `mesures`, `etat`, `prix`, `texte_visible` depuis le corps du webhook (chaîne vide par défaut).

- [ ] **Step 2: Les exposer dans le statut**

Dans `3EkEko4Qo2ofd7LK`, ajouter ces champs à l'objet de réponse et parser `inspi_texte` :

```js
const parse = s => { try { return JSON.parse(s || '[]'); } catch (e) { return []; } };
// dans l'objet renvoyé :
// marque: job.marque || '', taille: job.taille || '', mesures: job.mesures || '', etat: job.etat || '',
// prix: job.prix || '', texte_visible: String(job.texte_visible) === 'true',
// garment_en: job.garment_en || '', mannequin_desc: job.mannequin_desc || '', inspi_texte: parse(job.inspi_texte)
```

- [ ] **Step 3: Config du front** — dans `fES1vA8Ak6Vz9N6K` : `plans: ['porte_miroir', 'cintre', 'detail']` en dur, et `pastilles` construit depuis le prompt actif `config_pastilles` :

```js
const p = prompts.filter(x => x.nom === 'config_pastilles' && x.actif).sort((a, b) => b.version - a.version)[0];
const pastilles = p ? Object.entries(JSON.parse(p.texte)).map(([code, fragment]) => ({ code, fragment })) : [];
```

- [ ] **Step 4: Vérifier**

Run: `curl -s -H "X-VFN-Secret: $VFN_SECRET" $BASE/config | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["plans"], len(d.get("pastilles",[])))'`
Expected: `['porte_miroir', 'cintre', 'detail']` et `0` tant que `config_pastilles` n'est pas activé. Activer : `curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d '{"nom":"config_pastilles","version":1}' $BASE/prompts/activer`, relancer : `6`.

- [ ] **Step 5: Commit**

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, formulaire de fiche (marque, taille, mesures, état, prix, texte visible)"
```

---

### Task 5: Texte de la fiche (garment_en, titre en gabarit)

**Files:**
- Modifier dans n8n : `VFN — Générer le texte (sous-workflow)` (`gdGJLLnGtW79Jeol`)

**Interfaces:**
- Consumes : `prompts.texte_fiche` v3 (Task 2), champs de formulaire de `jobs` (Task 4).
- Produces : à la fin du sous-workflow, `jobs.titre` (gabarit), `jobs.description` (description LLM + lignes du formulaire), `jobs.garment_en`, `jobs.questions = '[]'`, `jobs.mood` inchangé (le mood est choisi à l'étape style).

- [ ] **Step 1: Activer `texte_fiche` v3**

Run: `curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d '{"nom":"texte_fiche","version":3}' $BASE/prompts/activer`

- [ ] **Step 2: Changer le schéma de sortie** dans le nœud `Construire la requête texte` : remplacer l'objet `schema` par

```js
schema: {
  type: 'object',
  properties: {
    description: { type: 'string' },
    garment_en: { type: 'string' }
  },
  required: ['description', 'garment_en'],
  additionalProperties: false
}
```
et remplacer la ligne `hint` par une version qui ajoute les données du formulaire (utiles pour le LLM) :
```js
const hint = ['Genre : ' + (job.genre || '') + '.', 'Type de vêtement : ' + (job.type_vetement || '') + '.', job.marque ? 'Marque : ' + job.marque + '.' : ''].filter(Boolean).join(' ');
```

- [ ] **Step 3: Adapter `Traiter la réponse`** — remplacer le corps du `try` par :

```js
let text = String($input.first().json.choices[0].message.content || '').trim();
if (text.startsWith('```')) text = text.replace(/^```(json)?/, '').replace(/```$/, '').trim();
let d;
try { d = JSON.parse(text); } catch (e1) { d = JSON.parse(repair(text)); }
if (!d.description || !d.garment_en) throw new Error('Champs manquants dans la réponse du modèle');
const titre = [job.type_vetement, job.marque].filter(Boolean).join(' ') + (job.taille ? ' — taille ' + job.taille : '');
const lignes = [job.marque && 'Marque : ' + job.marque, job.taille && 'Taille : ' + job.taille, job.mesures && 'Mesures : ' + job.mesures, job.etat && 'État : ' + job.etat].filter(Boolean).join('\n');
const description = d.description + (lignes ? '\n\n' + lignes : '');
const history = JSON.parse(job.historique || '[]');
history.push({ role: 'assistant', content: JSON.stringify(d) });
const cost = Number($input.first().json.usage?.cost || 0);
const versions = { ...(JSON.parse(job.prompt_versions || '{}')), texte_fiche: req.prompt_version };
if (req.exemples_ids && req.exemples_ids.length) versions.exemples = req.exemples_ids; else delete versions.exemples;
return [{ json: { ...base, statut: 'texte_pret', titre, description, garment_en: d.garment_en, mood: job.mood || '', questions: '[]', historique: JSON.stringify(history), cout_total: Number(job.cout_total || 0) + cost, prompt_versions: JSON.stringify(versions), erreur: '' } }];
```
Dans la branche `catch`, ajouter `garment_en: job.garment_en || ''`. Dans `Mettre à jour le job`, ajouter la colonne `garment_en` au mapping.

- [ ] **Step 4: Vérifier avec les photos PSG**

Run: `VFN_SECRET=... poc-annonces-n8n/scripts/test_job.sh homme haut poc-annonces/Test_humain/PSG/*.jpg` (adapter les extensions), puis `curl -s -H "X-VFN-Secret: $VFN_SECRET" "$BASE/job-status?id=<job_id>"`
Expected: `statut = texte_pret`, `titre` en gabarit, `description` de 2-3 phrases suivies des lignes du formulaire, `garment_en` en anglais (60-100 mots) mentionnant exactement le texte du maillot ; `questions = []` ; `cout_total` < 0,001 $.

- [ ] **Step 5: Vérifier l'affinage**

Run: `curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d '{"job_id":"<job_id>","message":"Ajoute que le maillot est de la saison 2023-2024"}' $BASE/job/texte` puis relire le statut.
Expected: `texte_pret`, description mise à jour. Si `Affiner le texte` (`bRdAbgJiiGKwNyvP`) référence `questions` ou `mood`, corriger la référence.

- [ ] **Step 6: Commit**

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, texte de fiche (garment_en, titre en gabarit)"
```

---

### Task 6: Style sans LLM et validation à l'humain

**Files:**
- Modifier dans n8n : `VFN — Sélectionner le style (sous-workflow)` (`FI9HyhPdvbATuSqw`), `VFN — Choisir le style (webhook)` (`ao81dPakf9IqTIyr`), `VFN — Valider le plan (webhook)` (`z1SY3ZkptHVSd4al`)

**Interfaces:**
- Consumes : `library.description_en`, `library.utilisations` (Tasks 1, 3), `prompts.config_mannequins` v2 (Task 2).
- Produces : `POST /job/style` `{job_id, moods_autorises?}` renvoie sans appel LLM une proposition écrite dans `jobs` : `decor_refs` (2 objets vision), `inspi_texte` (3 objets texte), `mannequin_desc`, `avertissements`, statut `en_attente_validation`. `POST /job/valider` `{job_id, mood, decor_refs?: [file_id] (max 2), inspi_texte?: [file_id] (max 3), garment_en?, mannequin_desc?, texte_visible?}` valide, enregistre, incrémente `library.utilisations` de chaque inspi retenue, passe en `generation_en_cours` et lance la génération.

- [ ] **Step 1: Activer les prompts de mannequin**

Run: `curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d '{"nom":"config_mannequins","version":2}' $BASE/prompts/activer`

- [ ] **Step 2: Supprimer la branche LLM du sous-workflow de style**

Dans `FI9HyhPdvbATuSqw`, supprimer les nœuds `Éclater les candidates`, `Télécharger la référence`, `Réduire la référence`, `Construire la requête de sélection`, `Choix du style (OpenRouter)`, `Traiter le choix`, `Marquer le job en erreur`, `Continuer sans référence` et le nœud `Des références existent ?`. Remplacer `Préparer la sélection` par ce Code node, relié directement à `Mettre à jour le job` :

```js
const job = $('Lire le job').first().json;
const rows = $('Lire la bibliothèque').all().map(i => i.json).filter(r => r.drive_file_id && r.actif);
const prompts = $('Lire les prompts').all().map(i => i.json).filter(p => p.actif);
const byName = n => {
  const p = prompts.filter(x => x.nom === n).sort((a, b) => b.version - a.version)[0];
  if (!p) throw new Error('Prompt actif introuvable : ' + n);
  return p;
};
const mann = byName('config_mannequins');
const cfg = JSON.parse(mann.texte);
const parseList = s => { try { const v = JSON.parse(s || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; } };
const allowed = parseList(job.moods_autorises);
const okMood = r => !allowed.length || parseList(r.moods).some(m => allowed.includes(m));
const warnings = [];
let pool = rows.filter(r => r.genre === job.genre && r.type_vetement === job.type_vetement && okMood(r));
if (!pool.length && job.genre) {
  pool = rows.filter(r => r.genre === job.genre && okMood(r));
  if (pool.length) warnings.push('Aucune référence ' + job.genre + ' / ' + job.type_vetement + ' avec ces moods : références d\'autres types proposées');
}
if (!pool.length) warnings.push('Aucune référence de style pour ce genre et ces moods : ambiance guidée par le mood seul');
pool.sort((a, b) => Number(b.utilisations || 0) - Number(a.utilisations || 0));
const card = r => ({ file_id: r.drive_file_id, nom_fichier: r.nom_fichier, type_vetement: r.type_vetement, moods: parseList(r.moods), tags: parseList(r.tags), description_en: r.description_en || '' });
const cards = pool.map(card);
const mannequin_desc = cfg[job.genre] || '';
if (!mannequin_desc) warnings.push('Pas de description de mannequin pour ce genre : personne générée librement');
const versions = { ...(JSON.parse(job.prompt_versions || '{}')), config_mannequins: mann.version };
return [{ json: {
  job_id: job.job_id, statut: 'en_attente_validation', mood: job.mood || '',
  decor_refs: JSON.stringify(cards.slice(0, 2)), inspi_texte: JSON.stringify(cards.slice(2, 5)),
  mannequin_desc, avertissements: JSON.stringify(warnings), mannequin_file_id: '',
  cout_total: Number(job.cout_total || 0), prompt_versions: JSON.stringify(versions), erreur: ''
} }];
```
Dans `Mettre à jour le job`, ajouter `inspi_texte` et `mannequin_desc` au mapping des colonnes. `Lire le job → Lire la bibliothèque → Lire les prompts → ce Code node → Mettre à jour le job`.

- [ ] **Step 3: Adapter le webhook `Choisir le style`** — s'il attend la fin du sous-workflow ou lit son résultat, garder la même interface ; retirer tout usage du coût LLM de sélection.

- [ ] **Step 4: Adapter `Valider le plan`** — lire d'abord `get_workflow_details z1SY3ZkptHVSd4al`. Étendre sa validation et son écriture :
  - `decor_refs` : chaque id doit exister et être actif dans `library` (règle existante) ; **max 2**, sinon 400 « 2 inspirations en vision maximum ».
  - `inspi_texte` (nouveau, liste de `file_id`) : mêmes contrôles, **max 3**, aucun id déjà présent dans `decor_refs` ; réécrire la colonne `jobs.inspi_texte` avec les objets `{file_id, nom_fichier, description_en}` relus dans `library`.
  - `garment_en`, `mannequin_desc`, `texte_visible` optionnels : s'ils sont fournis, mettre à jour `jobs`.
  - Incrémenter `utilisations` : pour chaque `file_id` de `decor_refs` + `inspi_texte` retenu, un nœud Data Table `update` sur `library` (filtre `drive_file_id`) avec `utilisations = {{ Number($json.utilisations || 0) + 1 }}` (relire la valeur courante).

- [ ] **Step 5: Vérifier (sans génération d'image)**

Run : sur le job de la Task 5, `curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d '{"job_id":"<job_id>"}' $BASE/job/style`, attendre 2 s, lire le statut.
Expected: `statut = en_attente_validation`, `decor_refs` de longueur ≤ 2, `inspi_texte` de longueur ≤ 3, `mannequin_desc` non vide, coût inchangé (0 $ ajouté). Vérifier 400 : `valider` avec 3 ids dans `decor_refs`. **Ne pas valider avec la génération avant la Task 7** (elle lancerait encore 4 plans) : tester `valider` avec le workflow `Générer les plans` désactivé ou après la Task 7.

- [ ] **Step 6: Commit**

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, sélection de style sans LLM, validation à choix humain"
```

---

### Task 7: Génération à 3 plans, sans check ni retry, inspirations et mannequin en texte

**Files:**
- Modifier dans n8n : `VFN — Tentative image (sous-workflow)` (`pGvWMH08Go4yGJYp`), `VFN — Générer un plan (sous-workflow)` (`HKMVyeJJQTSoBN6X`), `VFN — Générer les 4 plans (sous-workflow)` (`9Y0O9Z4MO9wVM0xB`), `VFN — Régénérer un plan (webhook)` (`MIeRXvNz9a4cwKIo`), `VFN — Écrire le journal Drive` (`LtGZGU42Lkx2ip3u`), `VFN — Feedback (webhook)` (`DgoKnyLMpuLqabFh`)

**Interfaces:**
- Consumes : `jobs.decor_refs` (vision), `jobs.inspi_texte`, `jobs.garment_en`, `jobs.mannequin_desc`, `jobs.texte_visible`, prompts de la Task 2.
- Produces : une tentative par plan, ligne `shots` avec `fidelite_ok` vide et `fidelite_verifiee = false`, `courant = true`, `brief` = prompt exact ; statut du job `galerie_prete` quand les 3 plans ont une tentative courante.

- [ ] **Step 1: Activer les prompts de génération**

```bash
for n in "brief_commun 2" "brief_ref_mannequin 2" "brief_plan_porte_sans_miroir 1" "brief_garment_en 1" "brief_inspi_texte 1"; do set -- $n; curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d "{\"nom\":\"$1\",\"version\":$2}" $BASE/prompts/activer; done
```

- [ ] **Step 2: Inventaire de `a_plat`**

Pour chaque workflow de la liste des fichiers et pour `front/index.html`, chercher la chaîne `a_plat` (`get_workflow_details`, puis recherche dans le JSON ; `grep -n a_plat poc-annonces-n8n/front/index.html`). Chaque occurrence est traitée aux étapes suivantes ou en Task 9. Aucune occurrence ne doit rester après la Task 9 (hors README historique et lignes `shots`/`feedback` existantes).

- [ ] **Step 3: Refaire `Préparer la tentative`** (tentative image) — remplacer la partie qui construit `decor`, `usesMannequin`, `refs` et `ctx` par :

```js
const parse = s => { try { const v = JSON.parse(s || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; } };
const decor = parse(job.decor_refs).slice(0, 2).map(d => d.file_id);
const inspiTexte = parse(job.inspi_texte).slice(0, 3);
const worn = plan === 'porte_miroir';
const planKey = worn && String(job.texte_visible) === 'true' ? 'porte_sans_miroir' : plan;
const refs = [
  ...photos.map(id => ({ role: 'vetement', file_id: id })),
  ...decor.map(id => ({ role: 'decor', file_id: id }))
];
const ctx = {
  ...base,
  extra,
  mood: job.mood || '',
  common: P('brief_commun').texte,
  ref_vetement: P('brief_ref_vetement').texte,
  ref_decor: P('brief_ref_decor').texte,
  garment: job.garment_en ? P('brief_garment_en').texte.replace('{garment_en}', job.garment_en) : '',
  inspi_texte: inspiTexte.length ? P('brief_inspi_texte').texte.replace('{liste}', inspiTexte.map((d, i) => (i + 1) + '. ' + d.description_en).join('\n')) : '',
  mannequin: worn && job.mannequin_desc ? P('brief_ref_mannequin').texte.replace('{mannequin_desc}', job.mannequin_desc) : '',
  plan_brief: P('brief_plan_' + planKey).texte,
  img,
  versions
};
return refs.map(r => ({ json: { ...r, skip: false, ctx } }));
```
Supprimer aussi la lecture de `check_fidelite` (`P('check_fidelite')`) et la clé `fidelite` du `ctx`.

- [ ] **Step 4: Refaire `Assembler la requête image`** — remplacer la construction de `parts` par :

```js
const roles = items.map(i => i.json.role);
const nV = roles.filter(r => r === 'vetement').length;
const nD = roles.filter(r => r === 'decor').length;
const parts = [ctx.common, ctx.ref_vetement.replace('{n}', nV)];
if (ctx.garment) parts.push(ctx.garment);
if (nD) parts.push(ctx.ref_decor.replace('{n}', nD));
if (ctx.inspi_texte) parts.push(ctx.inspi_texte);
if (ctx.mannequin) parts.push(ctx.mannequin);
parts.push('Overall mood: ' + ctx.mood + '.');
parts.push('SHOT: ' + ctx.plan_brief);
if (ctx.extra) parts.push('Extra instructions from the seller (they take priority): ' + ctx.extra);
const prompt = parts.join('\n\n');
```
(le reste du nœud : `fal_body`, `or_body`, `photo_urls` reste inchangé). Les images envoyées sont donc : photos du vêtement, puis 2 inspirations vision ; jamais le mannequin.

- [ ] **Step 5: Retirer le check de fidélité de la tentative**

Dans `pGvWMH08Go4yGJYp` : supprimer `Contrôle de fidélité (OpenRouter)` et le nœud `Verdict`, et remplacer `Construire la requête fidélité` par un Code node `Préparer l'enregistrement` qui garde le binaire et les champs attendus par `Envoyer l'image sur Drive` / `Enregistrer le plan` (lire ces deux nœuds pour lister les champs et reproduire les mêmes noms) :

```js
const ctx = $('Préparer la tentative').first().json.ctx;
const src = $("Extraire l'image OpenRouter").isExecuted ? $("Extraire l'image OpenRouter").first().json : $('Décider après Fal').first().json;
return { json: { image_cost: src.cout, fournisseur: src.fournisseur, name: ctx.plan + '_' + ctx.tentative + '.png', fidelite_ok: null, fidelite_problemes: '[]', fidelite_verifiee: false, retry_needed: false }, binary: $input.item.binary };
```
Reconnecter : `Télécharger l'image Fal` et `Image OpenRouter en fichier` → `Préparer l'enregistrement` → `Envoyer l'image sur Drive` → `Enregistrer le plan` → `Retirer le statut courant…` → `Résultat`. Dans `Enregistrer le plan`, fixer `cout = image_cost` (plus de coût de check) et vérifier que `fidelite_ok` accepte une valeur vide ; sinon écrire `false` et garder `fidelite_verifiee = false`.

- [ ] **Step 6: Retirer le retry de `Générer un plan`** (`HKMVyeJJQTSoBN6X`) — supprimer `Dérive de fidélité ?`, `Préparer la tentative 2`, `Tentative 2` ; relier `Tentative 1 → Relire les shots du job`. Dans `Décider le statut du job`, remplacer la liste : `const plans = ['porte_miroir', 'cintre', 'detail'];`.

- [ ] **Step 7: 3 plans dans le lanceur** — dans `9Y0O9Z4MO9wVM0xB` : remplacer la liste des plans (4 → 3) ; renommer le workflow `VFN — Générer les 3 plans (sous-workflow)`. Dans `MIeRXvNz9a4cwKIo` (régénérer) et `DgoKnyLMpuLqabFh` (feedback) : retirer `a_plat` des listes de plans acceptés. Dans `config_feedback` (prompt actif), retirer `plan:a_plat` s'il y figure, en nouvelle version.

- [ ] **Step 8: Journal** — dans `LtGZGU42Lkx2ip3u`, ajouter au `log.json` : `garment_en`, `mannequin_desc`, `inspi_texte`, `texte_visible`, formulaire (`marque`, `taille`, `mesures`, `etat`, `prix`) ; retirer toute référence à `mannequin_file_id` et aux verdicts de fidélité si le code plante sur des valeurs vides.

- [ ] **Step 9: Valider les workflows**

Run : `validate_workflow` sur chaque workflow modifié.
Expected: aucune erreur.

- [ ] **Step 10: Test réel (coût attendu ≈ 0,25 $ à 1K)**

Sur le job PSG de la Task 5 (style proposé, Task 6) : `curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d '{"job_id":"<job_id>","mood":"<un mood de la liste>"}' $BASE/job/valider`, attendre ~1 min, puis `poc-annonces-n8n/scripts/measure_cost.sh <job_id>`.
Expected: statut `galerie_prete`, exactement 3 plans (`porte_miroir`, `cintre`, `detail`), 1 tentative chacun, `cout_images` ≈ 0,24 $, `cout_texte` < 0,001 $. Ouvrir `shots.brief` d'un plan : contient `garment_en`, les descriptions d'inspirations en texte, et pour `porte_miroir` la description du mannequin ; ne contient pas de mention de retry.

- [ ] **Step 11: Commit**

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, génération à 3 plans sans check ni retry, inspirations et mannequin en texte"
```

---

### Task 8: Pastilles d'ajustement à la régénération

**Files:**
- Modifier dans n8n : `VFN — Régénérer un plan (webhook)` (`MIeRXvNz9a4cwKIo`)

**Interfaces:**
- Consumes : `prompts.config_pastilles` v1 (actif, Task 4).
- Produces : `POST /job/plan` accepte en plus `pastilles: ["trop_sombre", ...]` ; leurs fragments sont concaténés à `feedback` (avant la consigne libre) et passés comme `extra`. Code inconnu → 400 avec la liste autorisée.

- [ ] **Step 1: Lire** `get_workflow_details MIeRXvNz9a4cwKIo` et repérer le nœud qui construit `feedback` avant l'appel à `Générer un plan`.

- [ ] **Step 2: Ajouter un Code node** juste avant, avec la lecture de `prompts` (Data Table `get`, `returnAll`) en amont :

```js
const body = $('Webhook').first().json.body || {};
const prompts = $('Lire les prompts').all().map(i => i.json).filter(p => p.actif);
const p = prompts.filter(x => x.nom === 'config_pastilles').sort((a, b) => b.version - a.version)[0];
const map = p ? JSON.parse(p.texte) : {};
const codes = Array.isArray(body.pastilles) ? body.pastilles : [];
const unknown = codes.filter(c => !(c in map));
if (unknown.length) throw new Error('Pastilles inconnues : ' + unknown.join(', ') + ' (autorisées : ' + Object.keys(map).join(', ') + ')');
const fragments = codes.map(c => map[c]);
const free = String(body.feedback || '').trim();
return [{ json: { feedback: [...fragments, free].filter(Boolean).join(' ') } }];
```
(adapter le nom du nœud Webhook et remonter l'erreur en réponse 400 comme les autres validations du workflow).

- [ ] **Step 3: Vérifier (une régénération réelle, ~0,08 $)**

Run: `curl -s -X POST -H "X-VFN-Secret: $VFN_SECRET" -H 'Content-Type: application/json' -d '{"job_id":"<job_id>","plan":"cintre","pastilles":["trop_sature"],"feedback":""}' $BASE/job/plan`, attendre, lire `shots.brief` du plan `cintre` (dernière tentative).
Expected: le brief contient « Reduce colour saturation… » dans « Extra instructions from the seller » ; `pastilles: ["inconnue"]` → 400.

- [ ] **Step 4: Commit**

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, pastilles d'ajustement à la régénération"
```

---

### Task 9: Front — formulaire, grille de moods, « ce que l'IA va voir », galerie

**Files:**
- Modifier : `poc-annonces-n8n/front/index.html`

**Interfaces:**
- Consumes : `GET /config` (`plans`, `pastilles`, moods), `GET /library` (avec `description_en`, `utilisations`), `GET /job-status` (champs de la Task 4), `POST /job/style`, `POST /job/valider` (Task 6), `POST /job/plan` avec `pastilles` (Task 8), `POST /library/upload` (renvoie les `drive_file_id`).
- Produces : formulaire enrichi ; grille de moods ; sélection 2 vision + 3 texte ; écran de relecture éditable ; galerie 3 plans côte à côte avec étalonnage.

- [ ] **Step 1: Constante des plans** (`front/index.html:237`) :

```js
const PLAN_LABELS = { porte_miroir: "Porté", cintre: "Sur cintre", detail: "Détail" };
```

- [ ] **Step 2: Formulaire de création** — ajouter les champs `marque`, `taille`, `mesures`, `etat`, `prix` (inputs texte) et une case « Le vêtement porte du texte ou un logo lisible » ; les envoyer avec `fd.append(...)` au même endroit que `moods_autorises` (`front/index.html:495`), `texte_visible` valant `"true"` ou `"false"`. Pas de sélection multiple de moods à la création : le mood se choisit à l'étape style ; envoyer `moods_autorises` = tous par défaut.

- [ ] **Step 3: Affichage du texte** (`renderFiche`, `front/index.html:382-395`) — supprimer le bloc « Questions du modèle » (lignes 393-394) et le champ de feedback « réponse aux questions » devient « Feedback sur le texte » ; afficher `garment_en` dans un `textarea` éditable (envoyé à `valider`).

- [ ] **Step 4: Grille de moods et sélection d'inspirations** (dans `renderFiche`, bloc `inStyle`, lignes 399-412) — remplacer l'affichage des `decor_refs` par :
  - chips de moods (liste de `/config`) ; un clic filtre la grille, un second clic retire le filtre ;
  - grille des photos de la bibliothèque du genre/type de la fiche, triées par `utilisations` décroissant (les données viennent de `GET /library`), miniatures chargées comme aujourd'hui via `/image?id=` ;
  - deux états par photo : « Vision » (max 2) et « Texte » (max 3), exclusifs ; au chargement, préselection = `job.decor_refs` (vision) et `job.inspi_texte` (texte) ;
  - bouton « Utiliser comme inspi pour la génération » sur chaque photo de la bibliothèque = l'ajoute à la sélection (texte si les 2 places vision sont prises, sinon vision) ;
  - le mood retenu (`selectedMood`) est envoyé à `valider` ; le mood éditable libre (`#moodEdit`) devient un `select` limité à la liste fermée.

```js
const sel = { vision: [], texte: [] };
function toggleInspi(fileId, kind) {
  const other = kind === "vision" ? "texte" : "vision";
  sel[other] = sel[other].filter(id => id !== fileId);
  const max = kind === "vision" ? 2 : 3;
  if (sel[kind].includes(fileId)) sel[kind] = sel[kind].filter(id => id !== fileId);
  else if (sel[kind].length < max) sel[kind].push(fileId);
  else toast("Maximum " + max + " en " + kind);
  renderStyleGrid();
}
```

- [ ] **Step 5: Nouvelle inspi déposée pendant la fiche** — après l'appel `POST /library/upload`, lire les `drive_file_id` renvoyés et les ajouter à `sel.vision` (puis à `sel.texte` si plein), sans quitter la fiche.

- [ ] **Step 6: Écran « ce que l'IA va voir »** — remplacer le bouton de validation directe par un panneau affichant : `garment_en` (textarea), description du mannequin (`textarea` prérempli avec `mannequin_desc`), 2 miniatures vision, la liste des descriptions texte (lecture seule), et un choix « Photo portée : avec miroir / sans miroir » (préréglé sur `texte_visible`). Le bouton « Générer les 3 photos » appelle :

```js
await api("POST", "/job/valider", {
  job_id: job.job_id, mood: selectedMood,
  decor_refs: sel.vision, inspi_texte: sel.texte,
  garment_en: $("#garmentEn").value, mannequin_desc: $("#mannequinDesc").value,
  texte_visible: $("#photoSansMiroir").checked
});
```
Supprimer `#mannequinNote` (`front/index.html:132`, `:412`) : il n'y a plus de mannequin en image. Remplacer la mention de coût par « ~0,25 $ pour 3 photos ».

- [ ] **Step 7: Galerie** (`renderGallery`, `front/index.html:418-440`) :
  - retirer les avertissements de fidélité (`Fidélité non vérifiée`, `✓ Fidèle`, `problemes`, lignes 434-439) ;
  - afficher pour chaque plan la photo d'origine (première photo d'entrée) à gauche et l'image générée à droite ;
  - pastilles : une case à cocher par entrée de `config.pastilles`, envoyées dans `POST /job/plan` avec `feedback` ;
  - étalonnage à l'affichage et au téléchargement :

```js
function gradedDataUrl(img) {
  const c = document.createElement("canvas");
  c.width = img.naturalWidth; c.height = img.naturalHeight;
  const ctx = c.getContext("2d");
  ctx.filter = "saturate(0.82) sepia(0.10) contrast(0.97) brightness(1.02)";
  ctx.drawImage(img, 0, 0);
  ctx.filter = "none";
  ctx.globalAlpha = 0.06;
  for (let i = 0; i < 60000; i++) {
    ctx.fillStyle = Math.random() > 0.5 ? "#fff" : "#000";
    ctx.fillRect(Math.random() * c.width, Math.random() * c.height, 1, 1);
  }
  return c.toDataURL("image/jpeg", 0.92);
}
```
  Appliquer `gradedDataUrl` à l'image affichée et au lien de téléchargement ; un bouton « Voir brut » affiche l'image non étalonnée. Les paramètres (`saturate`, `sepia`) sont à régler à l'œil sur le maillot PSG en Task 10.

- [ ] **Step 8: Vérifier `a_plat` et `questions`**

Run: `grep -nE "a_plat|questions|mannequin_file_id|fidelite" poc-annonces-n8n/front/index.html`
Expected: aucune occurrence de `a_plat` ni de `mannequin_file_id` ; `questions` et `fidelite` absents ou inertes (jamais affichés).

- [ ] **Step 9: Vérifier dans le navigateur intégré** (`cd poc-annonces-n8n/front && python3 -m http.server 8765`, puis `http://127.0.0.1:8765`) : créer une fiche PSG jusqu'à l'écran « ce que l'IA va voir » (sans générer) et contrôler : grille triée, filtre par mood, limites 2/3, bouton d'inspi, textareas éditables, aucun message d'erreur dans la console (`read_console_messages`).

- [ ] **Step 10: Commit**

```bash
git add poc-annonces-n8n/front/index.html
git commit -m "poc-annonces-n8n: étape 9, front (formulaire, mood choisi, écran de relecture, galerie à 3 plans)"
```

---

### Task 10: Résolution, mesure du tarif, test de rendu, sauvegarde

**Files:**
- Modifier dans n8n : prompt `config_image` (v2 active), `README.md`

**Interfaces:**
- Consumes : tout ce qui précède.
- Produces : chiffres de coût avant/après consignés dans le README ; décision de résolution ; sauvegarde n8n à jour.

- [ ] **Step 1: Mesurer le tarif en 1K** — utiliser le test de la Task 7 (coût des 3 images) comme référence 1K. Noter `cout_images`.

- [ ] **Step 2: Tester 0,5K** — dans `config_image` v2, remplacer `"resolution": "1K"` par `"0.5K"` (si Fal refuse la valeur, lire l'erreur et essayer la valeur acceptée la plus basse), activer v2 (`POST /prompts/activer`), régénérer un plan `cintre` réel (~0,05-0,08 $) via `POST /job/plan`. Lire `cout` du plan dans `measure_cost.sh` et vérifier que l'en-tête `x-fal-billable-units` reflète bien un tarif plus bas ; sinon corriger `fal_cost_per_unit_usd` dans `config_image` pour que le coût affiché soit réel.

- [ ] **Step 3: Jugement de l'utilisateur** — comparer sur téléphone, pour le maillot PSG : ancienne fiche (`mufe74xl35gs` ou capture de la session) et nouvelle fiche, en 1K puis 0,5K. Décision de résolution : 0,5K si le texte « QATAR AIRWAYS » et les couleurs restent lisibles ; sinon rester en 1K (remettre v1 active).

- [ ] **Step 4: Régler l'étalonnage** — ajuster `saturate/sepia/contrast` de `gradedDataUrl` (Task 9, étape 7) avec l'utilisateur sur les 3 images du maillot jusqu'à ce que le vêtement et la pièce se lisent comme une même photo. Si l'écart reste visible, vérifier si un module d'image est autorisé dans les Code nodes de l'instance (`NODE_FUNCTION_ALLOW_EXTERNAL`) avant d'envisager un étalonnage côté serveur ; sinon consigner la limite.

- [ ] **Step 5: Test de bout en bout complet** avec un nouveau job PSG, depuis le front : formulaire → texte → mood + inspis → écran de relecture → 3 photos → régénération avec pastille → note finale. Contrôler : coût total < 0,20 $ sans régénération (sinon consigner l'écart et son poste), aucun retry dans `shots` (1 tentative par plan sans action manuelle), `log.json` présent dans le dossier Drive du job, `utilisations` incrémenté pour les inspirations retenues.

- [ ] **Step 6: Mettre à jour le README** — section « Étape 9 » : ce qui a changé (workflows, prompts et versions activées, colonnes), mesures avant/après, décision de résolution, écart d'étalonnage (front et non serveur), limites. Retirer des sections précédentes les affirmations devenues fausses (4 plans, retry, check de fidélité, sélection LLM).

- [ ] **Step 7: Sauvegarde** — exécuter `VFN — Sauvegarde (manuelle)` (`DD9ug6YEISQkIYgP`) dans n8n.

- [ ] **Step 8: Commit**

```bash
git add poc-annonces-n8n/README.md
git commit -m "poc-annonces-n8n: étape 9, mesures de coût et rendu, résolution, README"
```

---

## Auto-revue

- **Couverture de la spec** : plans à 3 (Task 7, 9) ; porté sans miroir si texte (Tasks 2, 4, 7, 9) ; suppression du check et du retry (Task 7) ; mood choisi, grille triée, filtre (Tasks 6, 9) ; 2 vision + 3 texte (Tasks 6, 7, 9) ; sélection sans LLM (Task 6) ; nouvelle inspi et bouton d'inspi (Tasks 3, 9) ; mannequin en texte (Tasks 2, 6, 7) ; `garment_en` en un seul appel, titre en gabarit, formulaire (Tasks 4, 5) ; pastilles (Tasks 2, 4, 8, 9) ; écran de relecture et côte à côte (Task 9) ; résolution, tarif, rendu (Task 10) ; étalonnage : front, écart signalé dans la spec et le README ; migration en texte des descriptions (Task 3).
- **Écart avec la spec** : `config_plans` a été abandonné (liste de plans en dur dans les workflows, exposée par `/config`) ; la spec est corrigée en conséquence.
- **Cohérence des noms** : `decor_refs` (vision), `inspi_texte`, `garment_en`, `mannequin_desc`, `texte_visible`, `config_pastilles`, `brief_plan_porte_sans_miroir`, `brief_garment_en`, `brief_inspi_texte` sont utilisés à l'identique dans toutes les tâches.
- **Limites du plan** : les modifications de nœuds existants (Verdict, Enregistrer le plan, Valider le plan, Régénérer un plan) dépendent d'un code que le plan demande de relire avant de modifier ; c'est volontaire, ces nœuds n'ont pas été reproduits ici.

# poc-annonces

Automatisation de la création de fiches Vinted : à partir de photo(s) brute(s) d'un vêtement, générer un texte d'annonce (SEO) et 4 photos stylées, fidèles au vêtement réel à l'œil, relues par un humain avant publication.

## Language

**Fiche**:
L'annonce Vinted complète (photos + texte) produite pour un article donné.
_Avoid_: Listing (sauf en anglais technique), annonce (trop générique)

**Bibliothèque**:
Le jeu de photos de référence personnel (stocké sur Google Drive, rangé par genre × type de vêtement, plus des dossiers `Mannequin/Homme` et `Mannequin/Femme`), utilisé comme seule source d'inspiration visuelle pour les photos générées.
_Avoid_: Banque d'images, décor library

**Mood**:
Le tag court décrivant le style/l'ambiance d'une fiche, déduit par le LLM des `decor_refs` choisies. Injecté dans le brief de chaque plan.
_Avoid_: Style (trop vague seul), ambiance

**decor_refs**:
Les 2-3 images choisies dans la bibliothèque, envoyées au modèle image comme références d'ambiance (lumière, décor, mood), jamais à copier. Un choix délibéré : plusieurs références faibles, jamais une seule référence déterministe.
_Avoid_: decor_id (mécanisme abandonné), décor unique

**Mannequin maison**:
L'image de référence du mannequin, générée une seule fois à partir d'une description fournie par l'utilisateur, sauvegardée et réutilisée telle quelle (jamais redécrite en texte) pour garder la même silhouette sur les photos portées. Ne montre jamais le visage. Envoyée au modèle image uniquement sur le plan `porte_miroir`. Sans mannequin pour un genre, le plan porté est quand même généré (personne libre).
_Avoid_: Modèle (ambigu avec "modèle LLM"), persona

**Plan**:
Une des 4 photos de sortie, fixes et toujours dans cet ordre : `porte_miroir` (porté, selfie miroir, visage caché par le téléphone), `a_plat`, `cintre`, `detail`. Chaque plan a son propre brief et déclenche un appel séparé au modèle image (pleine résolution, régénérable seul).
_Avoid_: Photo de sortie (ambigu), angle (les angles viennent des photos d'entrée)

**Harnais**:
Le code qui encadre le modèle image : les briefs par plan, l'assemblage des références et du prompt (`shots.py`), le check de fidélité et le retry. C'est là que se joue la qualité ; le modèle seul, avec un prompt vide, a donné le résultat catastrophique du POC initial.
_Avoid_: Prompt (le harnais est plus que le texte)

**Brief**:
Le texte envoyé au modèle image pour un plan : direction artistique commune (« effortless chic » parisien, UGC, 35mm, lumière naturelle, aucun rendu studio/CGI), ancrage de fidélité au vêtement, rôle de chaque image jointe, mood, puis consigne propre au plan.

**Fidélité**:
Garantie visée : le vêtement de la photo générée est reconnaissable à l'œil (couleur, imprimé, texte, liseré, coupe), pas identique au pixel. Le modèle regénère le vêtement, donc une dérive est possible ; d'où le check et la relecture humaine.
_Avoid_: Pixel-perfect (non garanti, abandonné avec le collage)

**Check de fidélité**:
Comparaison automatique par un LLM vision entre les photos d'origine et la photo générée, qui renvoie `{ok, problemes[]}`. Filet de sécurité, jamais un blocage : 1 retry automatique en cas de dérive, puis un flag visible dans la galerie. Une panne du check ne perd pas l'image.

**ShotResult**:
Le résultat d'un plan : image (ou erreur), verdict de fidélité, coût, nombre de tentatives. Un plan en échec n'arrête pas les autres.

**Galerie**:
L'écran de relecture après génération : les 4 plans avec avertissements, coût cumulé, case « Garder » et « Régénérer ce plan » avec consigne libre.

**decor_index.json**:
Le catalogue pré-calculé, produit une seule fois (hors ligne) par le script d'indexation de la bibliothèque : une entrée par photo de référence (chemin du dossier, description visuelle, tags de style). Lu par le pipeline principal à la place de ré-analyser toute la bibliothèque en vision à chaque fiche.
_Avoid_: Catalogue de moods

**PoC-1**:
Premier livrable, validé isolément : photo(s) → JSON (`titre`, `description`, `mood`, `questions`), via Streamlit, boucle de feedback en session.

**PoC-2 (V2)**:
Second livrable : indexation de la bibliothèque, sélection des `decor_refs`/mannequin, génération des 4 plans par modèle image natif (Gemini via OpenRouter), check de fidélité, galerie. Remplace la première version (segmentation Bria + inpainting Flux + composite via Fal.ai), abandonnée après le test humain du 2026-09-24 : elle ne pouvait pas produire de vêtement porté ni de cohérence, et son prompt était quasi vide.
_Avoid_: PoC-2 initial / Fal (abandonné)

**Validation**:
L'étape, dans la même fenêtre de chat que la génération du texte, où l'utilisateur approuve le plan (mood, `decor_refs`) avant que la génération d'image — coûteuse (~0,07 $ par plan) — ne soit déclenchée.

## Décisions à ne pas re-litiger

- Modèle image natif plutôt que collage : un composite garde l'angle et la lumière d'origine et ne peut pas mettre le vêtement sur une personne.
- 4 appels séparés plutôt qu'un collage 2×2 : résolution, régénération par plan. Repli prévu si la cohérence entre plans est insuffisante.
- Entrées attendues : photos brutes de téléphone, sans nettoyage de cadres.
- Spec : `specs/2026-09-24-poc2-v2-generation-native-design.md`. Plan : `plans/2026-09-24-poc2-v2-generation-native.md`.

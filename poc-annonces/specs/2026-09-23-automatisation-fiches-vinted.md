# Automatisation des fiches Vinted (PoC-1 + PoC-2)

## Problem Statement

Vendre régulièrement sur Vinted demande, pour chaque article : photographier le vêtement, rédiger un titre et une description accrocheurs, et produire des photos présentables (idéalement stylées, portées ou en situation). Fait manuellement, c'est lent et le résultat dépend de l'humeur du jour. Le vendeur veut un pipeline qui prend en charge la rédaction et la mise en scène photo à partir de simples photos brutes de l'article — sans jamais risquer de déformer le produit réel, ce qui exposerait à des litiges Vinted (le produit livré doit correspondre exactement à ce qui est montré).

## Solution

Un PoC en deux étages, chacun validable et testable isolément avant de passer au suivant.

**PoC-1** — Le vendeur dépose une ou plusieurs photos brutes d'un vêtement dans une interface Streamlit minimale. Un LLM avec vision (via OpenRouter) analyse les photos et produit un brouillon d'annonce structuré (titre, description, mood). Si des informations manquent pour trancher (matière ambiguë, coupe pas claire), le LLM pose au maximum 2-3 questions ciblées dans le même fil de chat. Le vendeur peut donner du feedback libre ("change le mood", "raccourcis la description") et le LLM régénère, en gardant l'historique de la session.

**PoC-2** — Construit sur PoC-1. Le vendeur maintient une bibliothèque personnelle de photos de référence sur Google Drive (rangée par genre × type de vêtement, plus des mannequins de référence). Un script d'indexation, exécuté une fois (puis à la demande), décrit chaque photo de la bibliothèque et met le résultat en cache. Lors de la génération d'une fiche, le LLM choisit 2-3 références de style (`decor_refs`) — et, pour les rendus "portés", une référence de mannequin — en se basant sur un jugement visuel réel restreint au sous-ensemble pertinent de la bibliothèque (même catégorie, même genre). Le vendeur voit un résumé du plan de génération (mood, références choisies, nombre et répartition des photos) et le valide avant que les appels de génération d'image (coûteux) ne soient déclenchés. Chaque photo de sortie est produite en préservant exactement les pixels du vêtement réel (segmentation + génération du décor autour + composite final), tandis que le décor/la pose peuvent s'inspirer librement de la bibliothèque.

## User Stories

1. En tant que vendeur, je veux déposer une ou plusieurs photos brutes d'un vêtement dans une interface simple, pour ne rien avoir à écrire au départ.
2. En tant que vendeur, je veux que le système génère automatiquement un titre, une description et un mood, pour ne pas rédiger moi-même le texte SEO.
3. En tant que vendeur, je veux voir le brouillon du LLM dans une interface de chat simple (Streamlit), pour le relire avant que quoi que ce soit ne soit généré côté image.
4. En tant que vendeur, je veux pouvoir donner un retour en texte libre ("change le mood", "mauvaise catégorie") et voir le LLM régénérer, pour itérer sans tout recommencer.
5. En tant que vendeur, je veux que le LLM ne me pose que les questions de clarification vraiment nécessaires (ex : matière ambiguë), pour ne pas être dérangé par des questions inutiles.
6. En tant que vendeur, je veux que les questions de clarification et la validation finale se déroulent dans la même fenêtre de chat, pour une expérience continue façon ChatGPT plutôt qu'un assistant à plusieurs écrans.
7. En tant que vendeur, je veux que l'historique de mes retours soit conservé pendant ma session (via `session_state`), pour ne pas avoir à répéter mes corrections. (La persistance au-delà de la session est un besoin futur, hors scope PoC — voir Out of Scope.)
8. En tant que vendeur, je veux que ma bibliothèque personnelle de photos de référence (Google Drive, rangée par genre × type de vêtement, plus des dossiers mannequins) soit la seule source d'inspiration visuelle des photos générées, pour que le résultat corresponde à mon goût.
9. En tant que vendeur, je veux que le système accède à mon Drive directement via une connexion autorisée une seule fois (service account), pour ne pas avoir à transférer des fichiers manuellement à chaque fois.
10. En tant que développeur, je veux que la bibliothèque soit indexée une fois hors ligne (`decor_index.json`) plutôt que ré-analysée en vision à chaque fiche, pour que la génération reste rapide et peu coûteuse.
11. En tant que développeur, je veux que le LLM n'examine en vision que les photos de référence pertinentes pour la catégorie et le genre de l'article (pas toute la bibliothèque), pour garder un matching précis sans exploser les coûts.
12. En tant que vendeur, je veux que le LLM choisisse 2-3 références de style lâches (pas une seule référence déterministe), pour que le résultat semble inspiré plutôt que recopié.
13. En tant que vendeur, je veux que les références proposées soient filtrées par type de vêtement identique (haut avec haut, bas avec bas, sac, chaussure, jupe, etc.) et par le bon genre, pour que les suggestions de style restent toujours pertinentes.
14. En tant que vendeur, je veux que la diversité de pose des photos de sortie vienne d'abord des références choisies dans la bibliothèque si elles en offrent plusieurs, et sinon des poses de mes photos d'entrée — mais jamais du mood/décor de mes photos d'entrée — pour avoir des poses variées sans jamais hériter du décor d'origine non désiré.
15. En tant que vendeur, je veux pouvoir régler le nombre de photos de sortie (3 par défaut) et la répartition porté/flatlay, pour tester différentes combinaisons.
16. En tant que vendeur, je veux qu'un mannequin "maison" cohérent soit réutilisé sur toutes les photos "portées" (généré une fois à partir de ma description, réutilisé comme référence image et non redécrit en texte à chaque fois), pour que toutes les photos portées montrent apparemment la même personne.
17. En tant que vendeur, je veux que ce mannequin maison ne montre jamais de visage (cadrage dès la génération, pas de flou en post-traitement), pour ne jamais générer ni montrer de visage identifiable.
18. En tant que vendeur, je veux que le genre du vêtement détecté détermine automatiquement si le mannequin homme ou femme est utilisé, pour que le style reste cohérent sans réglage manuel.
19. En tant que vendeur, je veux que les pixels réels du vêtement soient préservés à l'identique sur chaque photo générée (segmentés puis recomposés après génération), pour que ce qui est montré corresponde toujours exactement à ce qui est vendu.
20. En tant que vendeur, je veux voir un résumé texte du plan de génération (mood, références choisies, nombre/répartition des photos) avant que la génération d'image ne démarre, pour valider ou ajuster avant de payer l'étape coûteuse.
21. En tant que vendeur, je veux que l'absence d'un angle dans mes photos d'entrée produise simplement l'absence de sortie pour cet angle (jamais un angle inventé), pour ne jamais compromettre la fidélité au produit réel.
22. En tant que développeur, je veux que chaque photo de sortie soit générée indépendamment (même style choisi, sans garantie de cohérence de seed entre les sorties), pour garder le PoC simple tout en produisant une variété utilisable.
23. En tant que vendeur, je veux pouvoir ajouter de nouvelles photos dans mon Drive et relancer l'indexation manuellement, pour garder le catalogue à jour sans dépendre d'une synchronisation automatique pour le PoC.
24. En tant que développeur, je veux que tous les appels LLM (texte et vision) passent par OpenRouter plutôt qu'une API native, pour pouvoir changer de modèle librement sans changer le code d'intégration.
25. En tant que développeur, je veux démarrer avec les modèles les moins chers (`google/gemini-2.5-flash-lite` pour le texte/JSON, `fal-ai/bria/background/remove` + `fal-ai/flux-general/inpainting` pour les images) et des alternatives de repli documentées (`gpt-4o-mini`, `claude-haiku-4.5`, `flux-pro/kontext`), pour ne monter en qualité — et en coût — que si nécessaire.

## Implementation Decisions

**Ordre de construction** : PoC-1 d'abord, validé seul. Au sein de PoC-2 : (1) script d'indexation de la bibliothèque → `decor_index.json`, prérequis technique avant tout le reste ; (2) flux principal photo(s) → JSON enrichi (`decor_refs`) ; (3) génération d'image ; (4) contrôles UI (nombre de photos, répartition).

**Interface** : Streamlit pour les deux PoC (réutilise l'expérience du projet archivé). Un seul fil de chat par fiche, état conservé en `st.session_state` (aucune persistance disque pour le PoC).

**PoC-1 — schéma de sortie du LLM** : JSON avec les champs `titre`, `description`, `mood`, et un champ `questions` optionnel (tableau, vide si rien à clarifier). Le LLM décide lui-même s'il a besoin de précisions ; s'il en pose, l'écran de validation finale n'apparaît qu'une fois les questions résolues dans le même fil.

**PoC-1 — modèle** : `google/gemini-2.5-flash-lite` via OpenRouter par défaut (vision + JSON strict, moins cher). Repli : `openai/gpt-4o-mini`, puis `anthropic/claude-haiku-4.5` si la qualité de rédaction/mood déçoit.

**Bibliothèque Drive — accès** : Service account Google Cloud, dossier partagé une fois manuellement par le vendeur (pas d'OAuth utilisateur pour le PoC, pas de webhook de synchronisation — indexation relancée à la demande).

**Bibliothèque Drive — taxonomie constatée** (vérifiée en direct) :
```
Modèles photos/
├── Femme/{Chaussures, Jupe, Robe, Sac, Veste}
├── Homme/        (pas encore de sous-dossiers)
└── Mannequin/{Homme, Femme}
```
Le script d'indexation doit gérer les dossiers vides sans erreur (bibliothèque encore peu remplie).

**Script d'indexation** : parcourt la bibliothèque, appelle la vision une fois par photo, produit `decor_index.json` (chemin de dossier = genre + type, description visuelle courte, tags de style). Les dossiers `Mannequin/*` sont indexés séparément et jamais proposés comme `decor_refs` de style.

**Sélection des `decor_refs`** : filtrage d'abord par dossier (genre + type de vêtement détecté, sans coût), puis le LLM reçoit en vision les images du sous-ensemble filtré (borné, ~10 images) et choisit 2-3 `decor_refs` par jugement visuel réel — jamais uniquement sur la base de la description texte en cache. Le champ `mood` du JSON est dérivé de ce choix.

**Mannequin maison** : fourni par le vendeur lui-même (photos déposées dans `Mannequin/Homme` ou `Mannequin/Femme`), pas de génération de persona à la volée par le système. Choix homme/femme déterminé automatiquement par le genre détecté du vêtement.

**Pipeline de génération d'image, par photo de sortie** :
1. Segmentation du vêtement réel (`fal-ai/bria/background/remove`, ~0,018 $/image) pour obtenir un mask propre.
2. Génération du décor (`fal-ai/flux-general/inpainting`, ~0,075 $/MP) avec les `decor_refs` (+ la référence mannequin si sortie "portée") comme conditionnement IP-Adapter, mask = zone hors vêtement.
3. Composite final : les pixels originaux du vêtement sont replacés par-dessus la zone générée, pour garantir zéro déformation du produit.
- Coût estimé : ~0,10-0,15 $/photo, ~0,40-0,60 $ pour une fiche à 3-4 photos.
- Repli qualité : `fal-ai/flux-pro/kontext` (~0,055 $/MP) si le rendu ne convainc pas.
- VTON (FASHN, IDM-VTON) écarté : conçu pour habiller une personne existante, pas pour restyliser un décor autour d'un vêtement déjà photographié à plat — ajouterait une dépendance (photo de mannequin séparée) inutile ici.

**Nombre et répartition des sorties** : paramétrable dans l'UI (champ numérique/slider), 3 photos par défaut. Pas de ratio porté/flatlay figé — à ajuster par test.

**Correspondance angles** : une photo d'entrée manquante pour un angle donné ne produit aucune sortie pour cet angle (pas de génération d'angle inventé).

**Cohérence entre les sorties d'une même fiche** : même `decor_refs`/mannequin envoyés à chaque appel, mais appels indépendants (pas de seed partagée) — cohérence visuelle approximative acceptée pour le PoC.

## Testing Decisions

Deux seams, un par PoC, définis au point le plus haut possible (voir `../AGENTS.md`) :

- `generate_listing_draft(photos) -> ListingDraft` — frontière PoC-1. Les tests mockent la réponse HTTP d'OpenRouter (schéma JSON retourné), pas le contenu du prompt.
- `generate_listing_photos(photos, draft) -> list[Image]` — frontière PoC-2. Les tests mockent les réponses HTTP de Fal.ai (segmentation + inpainting), pas la logique de composite.

Tester le comportement externe (structure du JSON produit, nombre de photos de sortie cohérent avec le paramètre, absence de sortie pour un angle manquant, préservation des pixels du vêtement dans le composite) — jamais les détails d'implémentation (prompt exact, ordre interne des appels).

Pas de prior art directement réutilisable dans ce repo : les tests existants (`Archive/tests/`) couvrent l'ancien détecteur de tendances, un domaine indépendant.

## Out of Scope

- Persistance de l'historique de conversation au-delà de la session navigateur (besoin identifié pour une V1, pas pour le PoC).
- Synchronisation automatique de la bibliothèque Drive (webhook) — indexation manuelle à la demande pour le PoC.
- Interface pour ajouter de nouvelles photos d'inspiration à la bibliothèque depuis l'app — feature V1.
- Application métier complète (type AppSheet), gestion des ID uniques, KPIs financiers, multi-utilisateurs — vision long terme du document d'origine, hors PoC.
- Reproduction fidèle et déterministe d'un décor précis de la bibliothèque — la bibliothèque sert d'inspiration lâche, jamais de calque à reproduire à l'identique.
- Cohérence visuelle garantie (seed partagée, même scène) entre les 3-4 photos de sortie d'une même fiche.
- Pipelines VTON (virtual try-on) — écartés après recherche, ne correspondent pas au besoin (restyliser un décor autour d'un vêtement déjà photographié, pas habiller une personne).
- Plafond de budget / gouvernance de coût par fiche — laissé ouvert jusqu'à validation de la qualité du PoC.

## Further Notes

- Les prix des modèles (OpenRouter, Fal.ai) datent de la recherche menée pendant cette conversation (sept. 2026) et peuvent avoir changé — revérifier avant intégration dans le code.
- La bibliothèque Drive est vérifiée en accès direct (navigateur Chrome connecté au compte du vendeur) mais quasi vide au moment de cette spec (une seule photo test dans `Femme/Chaussures`) — le vendeur doit la peupler avant que PoC-2 soit testable de bout en bout.
- L'ancien projet Vinted (détecteur de tendances à fort taux de likes, notifications WhatsApp) est indépendant de cette feature et archivé dans `../Archive/` ; il pourra être réactivé séparément plus tard.

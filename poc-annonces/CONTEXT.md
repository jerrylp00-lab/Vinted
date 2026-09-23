# poc-annonces

Automatisation de la création de fiches Vinted : à partir de photo(s) brute(s) d'un vêtement, générer un texte d'annonce (SEO) et des photos stylées, en garantissant que le vêtement réel n'est jamais déformé.

## Language

**Fiche**:
L'annonce Vinted complète (photos + texte) produite pour un article donné.
_Avoid_: Listing (sauf en anglais technique), annonce (trop générique)

**Bibliothèque**:
Le jeu de photos de référence personnel (stocké sur Google Drive, rangé par genre × type de vêtement, plus des dossiers `Mannequin/Homme` et `Mannequin/Femme`), utilisé comme seule source d'inspiration visuelle pour les photos générées.
_Avoid_: Banque d'images, décor library

**Mood**:
Le tag court décrivant le style/l'ambiance d'une fiche, déduit par le LLM des `decor_refs` choisies.
_Avoid_: Style (trop vague seul), ambiance

**decor_refs**:
Les 2-3 images choisies dans la bibliothèque comme inspiration visuelle lâche pour les photos générées d'une fiche. Un choix délibéré : plusieurs références faibles, jamais une seule référence déterministe (rejeté — trop de fixation du modèle sur une seule image).
_Avoid_: decor_id (mécanisme abandonné), décor unique

**Mannequin maison**:
L'image de référence du mannequin, générée une seule fois à partir d'une description fournie par l'utilisateur, sauvegardée et réutilisée telle quelle (jamais redécrite en texte) pour garantir la même silhouette sur toutes les photos "porté". Ne montre jamais le visage (cadrage dès la génération).
_Avoid_: Modèle (ambigu avec "modèle LLM"), persona

**Porté / Flatlay**:
Les deux modes de présentation d'une photo de sortie. "Porté" = vêtement porté par le mannequin maison. "Flatlay" = vêtement à plat ou sur cintre, comme la présentation d'origine de la photo d'entrée.

**decor_index.json**:
Le catalogue pré-calculé, produit une seule fois (hors ligne) par le script d'indexation de la bibliothèque : une entrée par photo de référence (chemin du dossier, description visuelle, tags de style). Lu par le pipeline principal à la place de ré-analyser toute la bibliothèque en vision à chaque fiche.
_Avoid_: Catalogue de moods (le catalogue n'est plus une liste de labels fixes, mais l'index des vraies photos)

**PoC-1**:
Premier livrable, validé isolément : photo(s) → JSON (`titre`, `description`, `mood`, `questions`), via Streamlit, boucle de feedback en session.

**PoC-2**:
Second livrable, construit après PoC-1 : indexation de la bibliothèque, sélection des `decor_refs`/mannequin, génération multi-photos (segmentation + inpainting + composite).

**Validation**:
L'étape, dans la même fenêtre de chat que la génération du texte, où l'utilisateur approuve le plan (mood, `decor_refs`, répartition porté/flatlay) avant que la génération d'image — coûteuse — ne soit déclenchée.

# Spec — Réduction du coût par fiche, mood choisi par l'humain, image → texte

Date : 2026-09-25. Statut : issu d'une session de grilling, validé point par point par l'utilisateur. Complète `2026-09-24-backend-n8n-design.md` (les décisions non mentionnées ici restent celles de cette spec).

## Problème

Constat de l'utilisateur après usage :

1. **Coût par requête beaucoup trop élevé.** Mesure du 2026-09-24 (README, étape 4) : 0,40 $ d'images pour 4 plans, 0,56 $ avec une régénération. Cause : 4 générations d'image (~0,08 $ chacune) + retry automatique de fidélité qui double un plan + envoi de toutes les références en image à chaque appel. Le texte, la sélection de style et le check de fidélité coûtent des millièmes de dollar : le coût est dans l'image.
2. **Le mood est subi.** Le LLM vision choisit 2-3 références parmi 10 candidates tirées au sort, puis déduit un mood. L'utilisateur veut choisir son mood, ses inspirations et son mannequin, et que seules ces inspirations passent en génération.
3. **Trop de vision, pas assez de texte.** L'utilisateur veut décrire le vêtement, les inspirations et le mannequin en texte anglais détaillé, calculé une fois, et ne garder l'image que pour 2 inspirations.
4. **Rendu « IA ».** Couleurs trop vives ; le vêtement et l'environnement ne sont pas harmonieux (constaté sur le maillot PSG).

## Décisions

| Sujet | Décision |
|---|---|
| Plans | **3** : `porte_miroir` (porté), `cintre`, `detail`. `a_plat` supprimé. Les 3 sont générés d'un coup, en parallèle, tous générés par l'IA. |
| Porté | Si le vêtement porte du texte ou un logo lisible (case cochée au formulaire, corrigeable), le plan `porte_miroir` utilise le brief **sans miroir** (`brief_plan_porte_sans_miroir`, cadré du cou aux hanches) : le texte inversé par le miroir passait pour une dérive. Sinon brief miroir habituel. |
| Fidélité | **Plus de check automatique, plus de retry automatique.** Tout ajustement passe par l'humain (régénération). |
| Entrées vêtement | Toutes les photos d'entrée partent dans chaque appel image (pas de sélection). Bonne pratique de saisie : 2 bonnes photos plutôt que 3-4. |
| Mood | Choisi par l'utilisateur dans la liste fermée existante (`moods_liste`). La grille de la bibliothèque s'affiche par défaut triée par nombre d'utilisations, un clic sur un mood filtre. |
| Inspirations | **2 en vision** (images envoyées au modèle image), **2 à 3 en texte** (description anglaise longue). Pré-cochées : les plus utilisées du mood ; modifiables d'un clic. |
| Sélection de style | **Plus aucun appel LLM** (suppression du jugement visuel sur 10 images). Tri par `utilisations`, choix final par l'humain. |
| Nouvelle inspi | Déposée au moment de la fiche : indexée seule (1 appel vision, description anglaise 120-180 mots, éditable) puis utilisée d'office. Un bouton « Utiliser comme inspi » dans la bibliothèque ajoute une photo existante à la sélection. |
| Mannequin | **Aucune image.** Un profil homme et un profil femme, décrits en texte anglais (`config_mannequins` v2), affinés par l'utilisateur. Éditable à la validation. |
| Description du vêtement | Un seul appel vision par fiche produit `garment_en` (couleur, imprimé, texte, coupe, détails) + 2-3 phrases de description Vinted. `garment_en` est éditable et injecté dans les 3 briefs comme socle de fidélité. |
| Formulaire | L'utilisateur saisit au départ : genre, type, marque, taille, mesures, état, prix, « texte/logo visible ? ». Le titre est un gabarit. Le LLM n'invente ni marque ni taille. |
| Boucle de questions | Supprimée du schéma de sortie (`questions`, `mood`). L'affinage libre du texte reste. |
| Résolution | À tester en basse résolution (0,5K) ; on ne change que si l'écart est invisible sur téléphone. Tarif réel mesuré avant de figer un chiffre. |
| Rendu non-IA | (1) briefs : couleurs désaturées, étalonnage argentique, vêtement éclairé par la lumière de la pièce, léger froissé, non repassé ; (2) étalonnage commun appliqué aux 3 images. Voir « Étalonnage » ci-dessous. |
| Ajustement humain | Pastilles à un clic à la régénération (« trop sombre », « couleur fausse », « vêtement déformé », « trop mis en scène », « pièce trop rangée ») = fragments de prompt pré-écrits, en plus de la consigne libre. |
| Alignement humain/IA | Écran « ce que l'IA va voir » avant de lancer (tout en texte éditable) ; vue côte à côte photo d'origine / image générée. La mémoire de préférences est reportée. |

## Étalonnage (écart avec ce qui a été dit en session)

En session, l'étalonnage était annoncé « en Pillow ». Le back-end est n8n sans Python, et le node natif Edit Image n'a ni saturation ni grain. Décision : **étalonnage dans le front** (canvas : saturation réduite, léger chaud, grain), appliqué à l'affichage de la galerie et au téléchargement. Les fichiers Drive restent bruts. Repli si l'étalonnage back-end s'avère nécessaire : vérifier d'abord qu'un module d'image est autorisé dans les Code nodes de l'instance.

## Ce qui existe déjà et est réutilisé

- Bibliothèque : table `library` (`drive_file_id`, `moods` 1 à 3 parmi la liste fermée, `tags`, `description`, `actif`), liste de moods `moods_liste`, ajout de photos avec indexation automatique, aperçu d'image Drive.
- Prompts versionnés dans `prompts` (nouvelle version inactive → activation → retour arrière). **Tous les changements de prompt de cette spec sont de nouvelles versions**, activées à la main après test.
- Feedback 👍/👎 avec raisons, journal `log.json`, plafond de coût 1 $, repli Fal → OpenRouter.

## Modèle de données (changements)

- `library` : + `description_en` (string), + `utilisations` (number, défaut 0). `description` (français) reste comme archive.
- `jobs` : + `marque`, `taille`, `mesures`, `etat`, `prix` (strings), `texte_visible` (`"true"`/`"false"`), `garment_en`, `mannequin_desc`, `inspi_texte` (JSON `[{file_id, nom_fichier, description_en}]`). `decor_refs` désigne désormais les inspirations **en vision** (2 max, mêmes objets qu'aujourd'hui). `mannequin_file_id` n'est plus utilisé.
- `prompts` (nouvelles versions) : `brief_commun` v2, `brief_plan_porte_miroir` v2, `brief_plan_cintre` v2, `brief_plan_detail` v2, `brief_ref_mannequin` v2 (texte), `config_mannequins` v2 (genre → description anglaise), `config_image` v2 (résolution, coût), `texte_fiche` v3, `indexation_photo` v2 ; nouveaux : `brief_plan_porte_sans_miroir`, `brief_garment_en`, `brief_inspi_texte`, `config_pastilles`. La liste des 3 plans est en dur dans les workflows et exposée au front par `GET /config`.

## Flux cible

1. **Formulaire** : photos + genre, type, marque, taille, mesures, état, prix, « texte/logo visible ? », mood.
2. **Texte** (1 appel vision) → `garment_en` + description ; titre gabarit `"<Type> <Marque> — taille <Taille>"`.
3. **Style** : proposition sans LLM (2 vision + 3 texte, les plus utilisés du mood). L'utilisateur ajuste dans la grille (filtrable), dépose une nouvelle inspi si besoin, choisit le profil mannequin.
4. **Écran « ce que l'IA va voir »** : `garment_en`, description mannequin, inspis vision (images) et texte, mode miroir / sans miroir : tout éditable.
5. **Génération** : 3 plans en parallèle, une tentative chacun, résolution basse.
6. **Galerie** : côte à côte, étalonnage front, pastilles + consigne, « Garder », coût affiché.

Appels par fiche : 1 vision (texte) + 3 images. +1 vision par nouvelle inspi, une seule fois.

## Coût

- Estimation avant mesure : 3 × 0,08 $ = 0,24 $ à 1K sans régénération ; cible **< 0,20 $** sans régénération, à confirmer par mesure en 0,5K.
- Référence avant : 0,40 $ (4 plans) à 0,56 $ (avec régénération), mesures du README, étape 4.

## Critères de succès

1. Tarif réel mesuré sur le maillot PSG en 0,5K et en 1K, consigné dans le README.
2. Rendu « moins IA » jugé par l'utilisateur en avant/après sur le maillot PSG (mêmes photos d'entrée).

## Risques

- Le mannequin en texte seul fait varier la silhouette d'une fiche à l'autre (accepté).
- Les inspirations en texte suivent moins bien que des images ; l'ambiance du 3ᵉ plan peut s'atténuer.
- La basse résolution peut dégrader le texte du maillot ; à vérifier au test.
- Sans retry ni check, une dérive de fidélité n'est vue que par l'utilisateur : c'est voulu.

## Hors périmètre

- Mémoire de préférences alimentée par les 👍/👎 (reportée).
- Étalonnage côté serveur, publication automatique, authentification.
- Migration en vision des descriptions : on **traduit** les descriptions françaises existantes en texte (sans vision) ; refaire la vision seulement sur les photos jugées faibles.

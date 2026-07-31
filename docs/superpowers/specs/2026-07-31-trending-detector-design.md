# Trending Detector — Design

## Contexte

Bot Vinted actuel (`bot.py`) cherche par mot-clé et notifie tous les résultats. Besoin : détecter dans un flux de résultats les annonces avec une forte traction récente (beaucoup de likes en peu de temps), signal de forte demande, indépendamment de la marque recherchée.

## Règle de détection

Une annonce est "trending" si, au moment du check :

```
age_hours   <= max_age_hours   (défaut: 12)
favourite_count >= min_likes   (défaut: 50)
promoted == False
```

## Source des données

Un seul call à l'API catalogue existante (`/api/v2/catalog/items`, déjà utilisée par `search()`). Champs additionnels à extraire par item :

- `favourite_count` — nombre de likes
- `view_count` — nombre de vues
- `promoted` — annonce boostée (exclue de la règle)
- `photo.high_resolution.timestamp` — proxy de la date de publication/dernière modif de l'annonce (voir Limites)

`age_hours` = `(now_utc - photo_ts) / 3600`.

## Limites connues

- `photo.high_resolution.timestamp` n'est pas documenté officiellement par Vinted ; c'est un timestamp d'upload photo, pas un champ "date de création annonce" garanti.
- Si le vendeur ré-uploade une photo (édition de l'annonce), le timestamp est rafraîchi. Accepté comme comportement voulu : une ré-upload signale une action volontaire du vendeur, donc un âge "recalculé" est acceptable pour cette règle.
- Compteurs (`favourite_count`, `view_count`) sont un snapshot instantané au moment du call, pas un historique. Pas de mesure de vélocité (delta dans le temps) dans cette itération — écarté au profit du snapshot + seuil sur l'âge, plus simple.

## Composants

### `find_trending(query, min_likes=50, max_age_hours=12, exclude_promoted=True, limit=100)`

Ajoutée dans `bot.py`, à côté de `search()`. Réutilise `_get_session()`.

- GET `/api/v2/catalog/items` avec `search_text=query`, `per_page=limit` (**pas de `order=newest_first`** — testé en prod, ce tri ne renvoie que les toutes dernières annonces (< 20-30 min), donc favourite_count quasi toujours à 0 ; le tri par défaut de l'API, basé pertinence, remonte au contraire les annonces à forte traction quelle que soit leur fraîcheur)
- Pour chaque item : extrait `title`, `price`, `url` (comme `search()`), plus `favourite_count`, `view_count`, `promoted`, `photo_ts`
- Calcule `age_hours`
- Filtre selon la règle ci-dessus
- Retourne `[{title, price, url, favourite_count, view_count, age_hours}]`

**Validé en test réel** (2026-07-31, query "Chaussure", seuils 50 likes / 12h) : 1 résultat trouvé — "Escarpins noir vernis", 72 likes, 2h66, non promue.

### Script de test manuel

Petit script (`test_trending_manual.py`, jetable, non testé unitairement) qui appelle `find_trending("Chaussure")` et affiche les résultats en terminal. Pas de notification WhatsApp à ce stade.

## Hors scope (V2+)

- Déduplication / état persistant des items déjà alertés (nécessaire avant tout polling récurrent, sinon re-notification en boucle)
- Planificateur (cron / boucle) pour exécution périodique
- Intégration notify() / WhatsApp pour les items trending
- Mesure de vélocité par delta entre polls (écarté pour cette itération, voir Limites)

## Tests

Un test unitaire pytest (mock `_get_session`, suit le pattern des 9 tests existants) validant la logique de filtre (`age_hours`, `min_likes`, `promoted`) avec une horloge figée (`now` mocké) et des items fixtures couvrant les cas limites (juste sous/juste au-dessus des seuils, promoted=True).

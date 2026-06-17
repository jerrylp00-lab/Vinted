# Vinted Bot — Contexte projet

## Ce qui est fait (V1)

Script Python CLI (`bot.py`) qui scrape l'API publique Vinted et envoie les résultats sur WhatsApp via Twilio sandbox. Testé en prod — ça marche.

```bash
python3 bot.py --query "weston mocassin" --max-price 60 --limit 10
```

## Architecture V1

Un seul fichier `bot.py`, 3 fonctions :
- `_get_session()` — crée une `requests.Session`, visite `vinted.fr` pour obtenir les cookies de session (indispensable, sinon 403)
- `search(query, max_price, min_price, limit)` — GET `/api/v2/catalog/items`, retourne `[{title, price, url}]`
- `notify(items, query)` — envoie message WhatsApp via Twilio, fallback print terminal si erreur
- `main(args=None)` — argparse CLI, orchestre search + notify

## API Vinted (découverte en prod)

**Endpoint :** `https://www.vinted.fr/api/v2/catalog/items`

**Auth :** Pas de login, mais il faut d'abord faire un GET sur `https://www.vinted.fr` avec une vraie session pour obtenir les cookies. Sans ça → 403.

**Params utiles :**
- `search_text` — mot-clé
- `price_to`, `price_from` — filtres prix
- `per_page` — nb de résultats
- `order` — `newest_first`

**Structure d'un item dans la réponse :**
```json
{
  "id": 9095704044,
  "title": "Bottines Weston cuir noir",
  "price": { "amount": "450.0", "currency_code": "EUR" },
  "path": "/items/9095704044-bottines-weston",
  "brand_title": "J.M. Weston",
  "is_visible": true
}
```
URL complète = `https://www.vinted.fr` + `item["path"]`

**Headers nécessaires :**
```python
{
    "User-Agent": "Mozilla/5.0 (Macintosh; ...) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
}
```

## Config Twilio (WhatsApp sandbox)

Variables dans `.env` (ne jamais committer) :
```
TWILIO_SID=AC435a599eb79d94bf592189a157e684c1
TWILIO_TOKEN=<token>
FROM_WHATSAPP=whatsapp:+14155238886   # numéro sandbox Twilio
TO_WHATSAPP=whatsapp:+33768911908     # numéro destinataire
```

Prérequis sandbox : le destinataire doit avoir envoyé le code de jointure au numéro sandbox au préalable.

## Stack

- Python 3.13
- `requests==2.31.0`
- `twilio==8.13.0`
- `python-dotenv==1.0.1`
- `pytest==8.1.1`

## Tests

9 tests unitaires, tous passent. Mockent `_get_session` (pas `requests.get` directement) et `bot.Client`.

```bash
pytest tests/ -v
```

## Pistes V2

- **Multi-recherches** — lancer plusieurs recherches en parallèle (liste de queries dans un fichier config)
- **Déduplication** — stocker les IDs déjà vus (SQLite ou fichier JSON) pour n'envoyer que les nouvelles annonces
- **Polling automatique** — cron ou boucle qui tourne toutes les X minutes
- **Filtres avancés** — taille, marque, état (neuf/bon état), `catalog_ids` pour les catégories
- **API privée Vinted** — login avec session cookie `_vinted_fr_session` pour accéder aux endpoints authentifiés (favoris, messages, offres)
- **Multi-destinataires** — envoyer à plusieurs numéros WhatsApp
- **Dashboard** — petit front pour configurer les recherches sans CLI

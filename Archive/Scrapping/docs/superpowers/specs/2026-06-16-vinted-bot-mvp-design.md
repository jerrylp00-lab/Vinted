# Vinted Bot MVP — Design Spec
*Date: 2026-06-16*

## Objectif

Script Python CLI qui scrape l'API publique Vinted et envoie les résultats (titre, prix, lien) sur WhatsApp via Twilio sandbox. Critères de recherche passés en arguments CLI.

---

## Architecture

Un seul fichier `bot.py` avec deux responsabilités :

1. **`search(query, max_price, min_price, limit)`** — requête GET vers l'API publique Vinted, parse le JSON, retourne une liste de dicts `{title, price, url}`.
2. **`notify(items, query)`** — envoie un message WhatsApp formaté via Twilio SDK. Fallback print terminal si Twilio échoue.

```
bot.py
├── search()   → GET vinted.fr/api/v2/catalog/items → [{title, price, url}]
└── notify()   → Twilio WhatsApp → message formaté par item
```

---

## API Vinted (publique, sans login)

Endpoint : `https://www.vinted.fr/api/v2/catalog/items`

Params utilisés :
| Param | Arg CLI | Défaut |
|---|---|---|
| `search_text` | `--query` | requis |
| `price_to` | `--max-price` | aucun |
| `price_from` | `--min-price` | aucun |
| `per_page` | `--limit` | 10 |

Headers : `User-Agent` Mozilla standard pour éviter le blocage basique.

Réponse JSON parsée : `data.items[]` → `title`, `price`, `url`.

---

## Critères de recherche CLI

```bash
python bot.py --query "nike" --max-price 50 --min-price 10 --limit 5
```

Seul `--query` est obligatoire.

---

## Gestion des erreurs

| Cas | Comportement |
|---|---|
| HTTP 200, items trouvés | Envoie WhatsApp |
| HTTP 200, 0 items | WhatsApp "Aucune annonce trouvée pour [query]" |
| HTTP 429 (rate limit) | Print erreur, exit propre |
| Autre code HTTP | Print status code, exit propre |
| Twilio fail | Fallback print résultats dans terminal |

Pas de retry, pas de proxy — MVP de test uniquement.

---

## Format du message WhatsApp

```
🔍 Vinted — "nike" (5 résultats)

1. Nike Air Max 90 — 45€
   https://www.vinted.fr/items/...

2. Nike React — 30€
   https://www.vinted.fr/items/...
...
```

---

## Structure des fichiers

```
Testvinted/
├── bot.py
├── .env                # TWILIO_SID, TWILIO_TOKEN, FROM_WHATSAPP, TO_WHATSAPP
├── .env.example        # template sans valeurs sensibles
└── requirements.txt    # requests, twilio, python-dotenv
```

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # remplir avec les clés Twilio
python bot.py --query "nike" --max-price 50
```

---

## Hors scope (MVP)

- Login / session Vinted (API privée)
- Retry automatique
- Proxy / rotation d'IP
- Persistence / base de données
- Alertes périodiques automatiques

# Vinted Bot MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Script Python CLI qui scrape l'API publique Vinted et envoie les résultats (titre, prix, lien) sur WhatsApp via Twilio sandbox.

**Architecture:** Un seul fichier `bot.py` avec deux fonctions principales (`search` et `notify`) et un `main` qui orchestre le tout via argparse. Les tests mockent requests et Twilio pour rester rapides et sans dépendance réseau.

**Tech Stack:** Python 3, requests, twilio, python-dotenv, pytest, unittest.mock

---

### Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `tests/__init__.py`

- [ ] **Step 1: Créer .gitignore**

```
.env
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 2: Créer requirements.txt**

```
requests==2.31.0
twilio==8.13.0
python-dotenv==1.0.1
pytest==8.1.1
```

- [ ] **Step 3: Créer .env.example**

```
TWILIO_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_TOKEN=your_auth_token_here
FROM_WHATSAPP=whatsapp:+14155238886
TO_WHATSAPP=whatsapp:+33XXXXXXXXX
```

- [ ] **Step 4: Créer tests/__init__.py (vide)**

```bash
mkdir -p tests && touch tests/__init__.py
```

- [ ] **Step 5: Installer les dépendances**

```bash
pip install -r requirements.txt
```

Expected: pas d'erreur, twilio + requests + pytest installés.

- [ ] **Step 6: Commit**

```bash
git init
git add .gitignore requirements.txt .env.example tests/__init__.py
git commit -m "chore: scaffold project"
```

---

### Task 2: Fonction search()

**Files:**
- Create: `bot.py`
- Create: `tests/test_search.py`

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_search.py` :

```python
from unittest.mock import patch, MagicMock
from bot import search

MOCK_RESPONSE = {
    "items": [
        {
            "title": "Nike Air Max 90",
            "price": "45.00",
            "currency": "EUR",
            "url": "https://www.vinted.fr/items/123-nike-air-max-90"
        },
        {
            "title": "Nike React",
            "price": "30.00",
            "currency": "EUR",
            "url": "https://www.vinted.fr/items/456-nike-react"
        }
    ]
}

def test_search_returns_items():
    with patch("bot.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: MOCK_RESPONSE
        )
        results = search(query="nike", max_price=None, min_price=None, limit=10)
    assert len(results) == 2
    assert results[0]["title"] == "Nike Air Max 90"
    assert results[0]["price"] == "45.00 EUR"
    assert results[0]["url"] == "https://www.vinted.fr/items/123-nike-air-max-90"

def test_search_passes_correct_params():
    with patch("bot.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"items": []}
        )
        search(query="nike", max_price=50, min_price=10, limit=5)
    call_kwargs = mock_get.call_args
    params = call_kwargs[1]["params"]
    assert params["search_text"] == "nike"
    assert params["price_to"] == 50
    assert params["price_from"] == 10
    assert params["per_page"] == 5

def test_search_returns_empty_on_no_results():
    with patch("bot.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"items": []}
        )
        results = search(query="xyzxyz", max_price=None, min_price=None, limit=10)
    assert results == []

def test_search_raises_on_http_error():
    with patch("bot.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=429)
        try:
            search(query="nike", max_price=None, min_price=None, limit=10)
            assert False, "Should have raised"
        except SystemExit:
            pass
```

- [ ] **Step 2: Lancer le test — vérifier qu'il échoue**

```bash
pytest tests/test_search.py -v
```

Expected: `ModuleNotFoundError: No module named 'bot'` ou `ImportError`.

- [ ] **Step 3: Implémenter search() dans bot.py**

Créer `bot.py` (tous les imports au top — nécessaire pour que les mocks fonctionnent) :

```python
import sys
import os
import argparse
import requests
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

VINTED_API_URL = "https://www.vinted.fr/api/v2/catalog/items"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def search(query, max_price, min_price, limit):
    params = {"search_text": query, "per_page": limit}
    if max_price is not None:
        params["price_to"] = max_price
    if min_price is not None:
        params["price_from"] = min_price

    response = requests.get(VINTED_API_URL, params=params, headers=HEADERS)

    if response.status_code != 200:
        print(f"Erreur Vinted : HTTP {response.status_code}")
        sys.exit(1)

    items = response.json().get("items", [])
    return [
        {
            "title": item["title"],
            "price": f"{item['price']} {item['currency']}",
            "url": item["url"],
        }
        for item in items
    ]
```

- [ ] **Step 4: Lancer les tests — vérifier qu'ils passent**

```bash
pytest tests/test_search.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add bot.py tests/test_search.py
git commit -m "feat: add search() — scrape Vinted public API"
```

---

### Task 3: Fonction notify()

**Files:**
- Modify: `bot.py`
- Create: `tests/test_notify.py`

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_notify.py` :

```python
from unittest.mock import patch, MagicMock
from bot import notify

ITEMS = [
    {"title": "Nike Air Max 90", "price": "45.00 EUR", "url": "https://www.vinted.fr/items/123"},
    {"title": "Nike React", "price": "30.00 EUR", "url": "https://www.vinted.fr/items/456"},
]


def test_notify_sends_whatsapp_message():
    with patch("bot.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        with patch.dict("os.environ", {
            "TWILIO_SID": "ACtest",
            "TWILIO_TOKEN": "tokentest",
            "FROM_WHATSAPP": "whatsapp:+14155238886",
            "TO_WHATSAPP": "whatsapp:+33612345678"
        }):
            notify(ITEMS, query="nike")

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["from_"] == "whatsapp:+14155238886"
    assert call_kwargs["to"] == "whatsapp:+33612345678"
    assert "Nike Air Max 90" in call_kwargs["body"]
    assert "45.00 EUR" in call_kwargs["body"]
    assert "https://www.vinted.fr/items/123" in call_kwargs["body"]


def test_notify_empty_results_sends_no_results_message():
    with patch("bot.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        with patch.dict("os.environ", {
            "TWILIO_SID": "ACtest",
            "TWILIO_TOKEN": "tokentest",
            "FROM_WHATSAPP": "whatsapp:+14155238886",
            "TO_WHATSAPP": "whatsapp:+33612345678"
        }):
            notify([], query="xyzxyz")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "Aucune annonce" in call_kwargs["body"]


def test_notify_fallback_to_print_on_twilio_error(capsys):
    with patch("bot.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Twilio down")
        mock_client_class.return_value = mock_client
        with patch.dict("os.environ", {
            "TWILIO_SID": "ACtest",
            "TWILIO_TOKEN": "tokentest",
            "FROM_WHATSAPP": "whatsapp:+14155238886",
            "TO_WHATSAPP": "whatsapp:+33612345678"
        }):
            notify(ITEMS, query="nike")

    captured = capsys.readouterr()
    assert "Nike Air Max 90" in captured.out
```

- [ ] **Step 2: Lancer le test — vérifier qu'il échoue**

```bash
pytest tests/test_notify.py -v
```

Expected: `ImportError: cannot import name 'notify' from 'bot'`.

- [ ] **Step 3: Ajouter notify() dans bot.py**

Ajouter après la fonction `search` dans `bot.py` (les imports sont déjà en haut, ne pas les redupliquer) :

```python
def notify(items, query):
    if items:
        lines = [f"🔍 Vinted — \"{query}\" ({len(items)} résultats)\n"]
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {item['title']} — {item['price']}\n   {item['url']}\n")
        body = "\n".join(lines)
    else:
        body = f"Aucune annonce trouvée pour \"{query}\" sur Vinted."

    try:
        client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_TOKEN"])
        client.messages.create(
            from_=os.environ["FROM_WHATSAPP"],
            to=os.environ["TO_WHATSAPP"],
            body=body,
        )
        print("Message WhatsApp envoyé.")
    except Exception as e:
        print(f"Twilio erreur ({e}), affichage terminal :\n{body}")
```

- [ ] **Step 4: Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected: 7 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add bot.py tests/test_notify.py
git commit -m "feat: add notify() — send results to WhatsApp via Twilio"
```

---

### Task 4: CLI — main() avec argparse

**Files:**
- Modify: `bot.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Écrire le test qui échoue**

Créer `tests/test_cli.py` :

```python
from unittest.mock import patch, MagicMock
from bot import main


def test_main_calls_search_and_notify():
    items = [{"title": "Nike", "price": "40.00 EUR", "url": "https://vinted.fr/items/1"}]
    with patch("bot.search", return_value=items) as mock_search, \
         patch("bot.notify") as mock_notify:
        main(["--query", "nike", "--max-price", "50", "--min-price", "10", "--limit", "5"])

    mock_search.assert_called_once_with(
        query="nike", max_price=50.0, min_price=10.0, limit=5
    )
    mock_notify.assert_called_once_with(items, query="nike")


def test_main_query_required():
    try:
        main([])
        assert False, "Should have raised SystemExit"
    except SystemExit:
        pass
```

- [ ] **Step 2: Lancer le test — vérifier qu'il échoue**

```bash
pytest tests/test_cli.py -v
```

Expected: `ImportError: cannot import name 'main' from 'bot'`.

- [ ] **Step 3: Ajouter main() et le bloc __main__ dans bot.py**

Ajouter à la fin de `bot.py` (argparse déjà importé en haut) :

```python
def main(args=None):
    parser = argparse.ArgumentParser(description="Vinted bot — recherche d'annonces")
    parser.add_argument("--query", required=True, help="Mot-clé de recherche")
    parser.add_argument("--max-price", type=float, help="Prix maximum (€)")
    parser.add_argument("--min-price", type=float, help="Prix minimum (€)")
    parser.add_argument("--limit", type=int, default=10, help="Nombre de résultats (défaut: 10)")
    parsed = parser.parse_args(args)

    items = search(
        query=parsed.query,
        max_price=parsed.max_price,
        min_price=parsed.min_price,
        limit=parsed.limit,
    )
    notify(items, query=parsed.query)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected: 9 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add bot.py tests/test_cli.py
git commit -m "feat: add CLI — argparse main() wires search + notify"
```

---

### Task 5: Test d'intégration réel

**Prérequis:** `.env` rempli avec tes vraies clés Twilio + WhatsApp sandbox activé.

- [ ] **Step 1: Copier .env.example en .env et remplir**

```bash
cp .env.example .env
# Éditer .env avec tes valeurs Twilio
```

- [ ] **Step 2: Lancer une vraie recherche**

```bash
python bot.py --query "nike" --max-price 50 --limit 3
```

Expected dans le terminal :
```
Message WhatsApp envoyé.
```

Et sur ton WhatsApp : message avec 3 annonces Nike à moins de 50€.

- [ ] **Step 3: Tester avec 0 résultat**

```bash
python bot.py --query "xyzxyz123abc" --limit 3
```

Expected sur WhatsApp :
```
Aucune annonce trouvée pour "xyzxyz123abc" sur Vinted.
```

- [ ] **Step 4: Commit final**

```bash
git add .env.example
git commit -m "chore: add .env.example — integration test passed"
```

> Ne jamais committer `.env` (contient des clés secrètes). Vérifier que `.gitignore` contient `.env`.


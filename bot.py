import os
import argparse
import time
import requests
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

VINTED_HOME = "https://www.vinted.fr"
VINTED_API_URL = "https://www.vinted.fr/api/v2/catalog/items"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def _get_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(VINTED_HOME, timeout=10)
    return session


def search(query, max_price, min_price, limit):
    params = {"search_text": query, "per_page": limit, "order": "newest_first"}
    if max_price is not None:
        params["price_to"] = max_price
    if min_price is not None:
        params["price_from"] = min_price

    session = _get_session()
    response = session.get(VINTED_API_URL, params=params, timeout=10)

    if response.status_code != 200:
        raise requests.HTTPError(f"Erreur Vinted : HTTP {response.status_code}", response=response)

    items = response.json().get("items", [])
    return [
        {
            "title": item["title"],
            "price": f"{item['price']['amount']} {item['price']['currency_code']}",
            "url": f"https://www.vinted.fr{item['path']}",
        }
        for item in items
    ]


def find_trending(query, min_likes=50, max_age_hours=12, exclude_promoted=True, limit=100):
    params = {"search_text": query, "per_page": limit}

    session = _get_session()
    response = session.get(VINTED_API_URL, params=params, timeout=10)

    if response.status_code != 200:
        raise requests.HTTPError(f"Erreur Vinted : HTTP {response.status_code}", response=response)

    now = time.time()
    trending = []
    for item in response.json().get("items", []):
        photo_ts = (item.get("photo") or {}).get("high_resolution", {}).get("timestamp")
        if photo_ts is None:
            continue
        age_hours = (now - photo_ts) / 3600
        favourite_count = item.get("favourite_count", 0)
        promoted = item.get("promoted", False)

        if age_hours > max_age_hours:
            continue
        if favourite_count < min_likes:
            continue
        if exclude_promoted and promoted:
            continue

        trending.append({
            "title": item["title"],
            "price": f"{item['price']['amount']} {item['price']['currency_code']}",
            "url": f"https://www.vinted.fr{item['path']}",
            "favourite_count": favourite_count,
            "view_count": item.get("view_count", 0),
            "age_hours": round(age_hours, 2),
        })

    return trending


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

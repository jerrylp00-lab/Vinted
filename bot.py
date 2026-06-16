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

    response = requests.get(VINTED_API_URL, params=params, headers=HEADERS, timeout=10)

    if response.status_code != 200:
        raise requests.HTTPError(f"Erreur Vinted : HTTP {response.status_code}", response=response)

    items = response.json().get("items", [])
    return [
        {
            "title": item["title"],
            "price": f"{item['price']} {item['currency']}",
            "url": item["url"],
        }
        for item in items
    ]


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

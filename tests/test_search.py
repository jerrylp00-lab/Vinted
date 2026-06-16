from unittest.mock import patch, MagicMock
import pytest
import requests
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
        with pytest.raises(requests.HTTPError):
            search(query="nike", max_price=None, min_price=None, limit=10)

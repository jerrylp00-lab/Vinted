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

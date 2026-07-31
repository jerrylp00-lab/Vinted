from unittest.mock import patch, MagicMock
from bot import find_trending

NOW = 1_700_000_000  # horloge figée pour les tests

def _item(id_, favs, promoted, age_hours):
    return {
        "id": id_,
        "title": f"Item {id_}",
        "price": {"amount": "10.00", "currency_code": "EUR"},
        "path": f"/items/{id_}-item",
        "favourite_count": favs,
        "view_count": 0,
        "promoted": promoted,
        "photo": {"high_resolution": {"timestamp": NOW - age_hours * 3600}},
    }

MOCK_RESPONSE = {
    "items": [
        _item(1, favs=60, promoted=False, age_hours=1),    # trending
        _item(2, favs=49, promoted=False, age_hours=1),     # juste sous seuil likes
        _item(3, favs=60, promoted=False, age_hours=13),    # juste au-dessus seuil age
        _item(4, favs=60, promoted=True, age_hours=1),      # promoted, exclu
        _item(5, favs=50, promoted=False, age_hours=12),    # pile aux seuils -> inclus
    ]
}

def test_find_trending_filters_correctly():
    with patch("bot._get_session") as mock_session_fn, patch("bot.time.time", return_value=NOW):
        mock_session = MagicMock()
        mock_session_fn.return_value = mock_session
        mock_session.get.return_value = MagicMock(
            status_code=200,
            json=lambda: MOCK_RESPONSE
        )
        results = find_trending("chaussure", min_likes=50, max_age_hours=12)

    ids = [r["title"] for r in results]
    assert ids == ["Item 1", "Item 5"]
    assert results[0]["favourite_count"] == 60
    assert results[0]["age_hours"] == 1.0

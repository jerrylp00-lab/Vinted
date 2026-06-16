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

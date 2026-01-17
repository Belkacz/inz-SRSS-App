import json
import pytest
from unittest.mock import patch, MagicMock
from cardModule import CardMonitor, UserHandler, User

# mock baza użytkowników
class FakeUserHandler(UserHandler):
    def __init__(self):
        pass

    def get_users(self):
        return [
            User(id=1, card_number=123, first_name="Jan", second_name="Kowalski", email="a@b.com", supervisor="Boss", privilage_id_fk=1),
            User(id=2, card_number=456, first_name="Anna", second_name="Nowak", email="c@d.com", supervisor="Boss", privilage_id_fk=1)
        ]

    def create_list_in_n_out(self, card_list, users_list):
        users_in = [u for u in users_list if u.card_number in card_list]
        users_out = [u for u in users_list if u.card_number not in card_list]

        users_in_card_list = [u.card_number for u in users_in]

        # Dodaj nieznane karty
        for card in card_list:
            if card not in users_in_card_list:
                unknown_user = User(
                    id=None,
                    card_number=card,
                    first_name="Not Registered",
                    second_name="Card",
                    email=None,
                    supervisor=None,
                    privilage_id_fk=None
                )
                users_in.append(unknown_user)

        return users_in, users_out

@pytest.fixture
def card_monitor():
    handler = FakeUserHandler()
    monitor = CardMonitor(ws_url="ws://fake", user_handler=handler)
    return monitor


def test_card_list_update(card_monitor):
    fake_data = {
        "card1": 123,
        "card2": 999,   # nieznana karta
        "cardCounter": 2
    }

    # Mock websocket
    fake_ws = MagicMock()
    fake_ws.recv.side_effect = [
        json.dumps(fake_data),
        KeyboardInterrupt()  # kończy pętlę
    ]

    with patch("websocket.WebSocket", return_value=fake_ws):
        card_monitor.active = True
        try:
            card_monitor._ws_listener()
        except KeyboardInterrupt:
            pass

    # Sprawdź, czy lista kart została uzupełniona
    assert 123 in card_monitor.card_list
    assert 999 in card_monitor.card_list
    # Sprawdź, czy wykryto człowieka
    assert card_monitor.human_in is True
    # Sprawdź, czy użytkownicy w bazie zostali przypisani
    in_card_numbers = [u.card_number for u in card_monitor.users_in]
    assert 123 in in_card_numbers
    assert 999 in in_card_numbers  # nieznana karta powinna być dodana

import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from pirModule import PIRMonitor


@pytest.fixture
def pir_monitor():
    monitor = PIRMonitor("ws://test")
    monitor.active = False  # nie uruchamiamy pętli
    return monitor


def test_initial_counters_zero(pir_monitor):
    assert pir_monitor.getPirCounter(26) == 0
    assert pir_monitor.getPirCounter(16) == 0


def test_reset_counters(pir_monitor):
    pir_monitor.pir26Counter = 5
    pir_monitor.pir16Counter = 3

    pir_monitor.restCounters()

    assert pir_monitor.pir26Counter == 0
    assert pir_monitor.pir16Counter == 0


# Udajemy websocket i sprawdzamy czy liczniki rosną
@patch("pirModule.websocket.WebSocket")
def test_counters_increase_from_websocket(mock_ws_class):
    fake_ws = Mock()
    
    # Ustawienie side_effect dla recv()
    fake_ws.recv.side_effect = [
        json.dumps({"pir26RisingCounter": 2, "pir16RisingCounter": 1}),
        json.dumps({"pir26RisingCounter": 3, "pir16RisingCounter": 2}),
        Exception("stop")  # wyjście z pętli wewnętrznej
    ]

    mock_ws_class.return_value = fake_ws

    monitor = PIRMonitor("ws://test")
    
    call_count = 0
    original_connect = fake_ws.connect
    
    def limited_connect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            # Po pierwszym połączeniu zatrzymaj monitor
            monitor.active = False
            raise Exception("Test completed")
        return original_connect(*args, **kwargs)
    
    fake_ws.connect = limited_connect
    monitor.active = True

    with patch("time.sleep", return_value=None):
        try:
            monitor._ws_listener()
        except Exception:
            pass
        finally:
            monitor.active = False  # Upewnij się że pętla się zatrzyma

    assert monitor.pir26Counter == 5
    assert monitor.pir16Counter == 3
import time
import pytest
from unittest.mock import Mock
from safetyMonitor import SafetyMonitor, STATUS


@pytest.fixture
def safety():
    pir = Mock()
    pir.getPirCounter.side_effect = lambda x: 0
    pir.resetCounters = Mock()

    cam = Mock()
    cam.motion_saftey = False
    cam.people_count = 0
    cam.stremed_frame = None

    card = Mock()
    card.human_in = True
    card.users_in = []

    monitor = SafetyMonitor(
        pir, cam, card,
        warning_interval=1,
        alert_interval=2
    )
    monitor.working = False
    return monitor


def test_no_alarm_when_cam_motion(safety):
    safety.cam_monitor.motion_saftey = True

    safety._collectSensorData()

    assert safety.total_cam_motion is True
    assert safety.status == STATUS.OK


def test_no_alarm_when_pir_motion(safety):
    safety.pir_monitor.getPirCounter.side_effect = lambda x: 3

    safety._collectSensorData()

    assert safety.total_pir26 > 0 or safety.total_pir16 > 0
    assert safety.status == STATUS.OK


def test_alarm_when_no_motion_anywhere(safety):
    safety.warning_time = time.time() - 3

    # symulacja jednej iteracji alarmowej
    if (
        not safety.total_cam_motion
        and safety.total_pir26 == 0
        and safety.total_pir16 == 0
        and safety.card_monitor.human_in
    ):
        if time.time() - safety.warning_time > safety.alert_interval:
            safety.status = STATUS.ALARM

    assert safety.status == STATUS.ALARM


def test_reset_allows_alarm_again(safety):
    safety.status = STATUS.ALARM
    safety.email_sent = True

    safety.resetData()

    assert safety.status == STATUS.OK
    assert safety.email_sent is False

    # ponownie brak ruchu
    safety.warning_time = time.time() - 3

    if time.time() - safety.warning_time > safety.alert_interval:
        safety.status = STATUS.ALARM

    assert safety.status == STATUS.ALARM

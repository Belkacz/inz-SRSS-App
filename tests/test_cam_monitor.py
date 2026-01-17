import json
import pytest
from camModule import CAMMonitor


@pytest.fixture
def cam_monitor():
    cam = CAMMonitor("ws://test")
    cam.active = False
    return cam


def test_motion_json_sets_motion(cam_monitor):
    msg = json.dumps({
        "motion": True,
        "timestamp": 1700000000
    })

    motion = cam_monitor._handle_motion_json(msg)

    assert motion is True
    assert cam_monitor.motion_detected is True
    assert cam_monitor.last_motion_time is not None
    assert cam_monitor.json_counter == 1


def test_motion_json_no_motion(cam_monitor):
    msg = json.dumps({
        "motion": False,
        "timestamp": 1700000000
    })

    motion = cam_monitor._handle_motion_json(msg)

    assert motion is False
    assert cam_monitor.motion_detected is False


def test_invalid_json_does_not_crash(cam_monitor):
    motion = cam_monitor._handle_motion_json("{invalid json")

    assert motion is None

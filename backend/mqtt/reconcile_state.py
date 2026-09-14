"""In-memory record of which devices/cameras were seen on MQTT this reconciliation window.

No Django imports on purpose -- just a thread-safe scratch pad the paho
network thread writes to as messages arrive, read by
monitoring/services/mqtt_reconciliation.py once a window closes. Kept
separate to avoid a circular import (mqtt and monitoring already import
from each other elsewhere).
"""

import threading

_lock = threading.Lock()
_active = False
_seen_device_ids = set()
_seen_camera_ids = set()


def begin_cycle() -> None:
    """Start a new reconciliation window: forget whatever was seen before."""

    global _active

    with _lock:
        _seen_device_ids.clear()
        _seen_camera_ids.clear()
        _active = True


def record_device_seen(device_id) -> None:
    """Note that this device produced an MQTT message during the current window."""

    with _lock:
        if _active:
            _seen_device_ids.add(device_id)


def record_camera_seen(camera_id) -> None:
    """Note that this camera produced an MQTT message during the current window."""

    with _lock:
        if _active:
            _seen_camera_ids.add(camera_id)


def snapshot_and_reset() -> tuple[set, set]:
    """
    Close the current window and return (seen_device_ids, seen_camera_ids).

    Recording stops immediately (any message arriving after this call is
    treated as belonging to the *next* window, not this one).
    """

    global _active

    with _lock:
        seen_devices = set(_seen_device_ids)
        seen_cameras = set(_seen_camera_ids)
        _seen_device_ids.clear()
        _seen_camera_ids.clear()
        _active = False

    return seen_devices, seen_cameras

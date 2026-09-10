"""
In-memory tracking of which devices/cameras have been seen on MQTT during
the current reconciliation window.

Deliberately kept free of Django model/app imports -- it's just a
thread-safe scratch pad that the subscriber writes to (from the paho
network thread) as messages arrive, and that
monitoring/services/mqtt_reconciliation.py reads from once a window
closes. Splitting it out this way avoids a circular import between the
mqtt and monitoring apps, which already import from each other elsewhere
(mqtt/service.py -> monitoring services, monitoring/services/
camera_monitor.py -> mqtt/provisioning.py).
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

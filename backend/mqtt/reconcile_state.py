# keeps in memory which devices and cameras were seen on mqtt during the current reconciliation window

import threading

_lock = threading.Lock()
_active = False
_seen_device_ids = set()
_seen_camera_ids = set()


# starts a new window and forgets what was seen before
def begin_cycle() -> None:
    global _active

    with _lock:
        _seen_device_ids.clear()
        _seen_camera_ids.clear()
        _active = True


# notes that this device sent a message during the window
def record_device_seen(device_id) -> None:
    with _lock:
        if _active:
            _seen_device_ids.add(device_id)


# notes that this camera sent a message during the window
def record_camera_seen(camera_id) -> None:
    with _lock:
        if _active:
            _seen_camera_ids.add(camera_id)


# closes the window and returns the ids of the seen devices and cameras
def snapshot_and_reset() -> tuple[set, set]:
    global _active

    with _lock:
        seen_devices = set(_seen_device_ids)
        seen_cameras = set(_seen_camera_ids)
        _seen_device_ids.clear()
        _seen_camera_ids.clear()
        _active = False

    return seen_devices, seen_cameras

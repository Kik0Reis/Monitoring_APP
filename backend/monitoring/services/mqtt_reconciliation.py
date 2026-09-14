"""Answers "does the broker still know this device/camera exists?" -- not a timeout check.

That's a different question from OFFLINE status (heartbeat_monitor.py
handles missed heartbeats). This is for cases like deleting a Country and
MQTT traffic re-creating some of that tree from scratch -- some records
may no longer match anything the broker actually retains.

subscriber.py periodically forces the broker to resend every retained
message (unsubscribe + resubscribe) and records who replies within a
short window (mqtt/reconcile_state.py). This module closes that window:
anyone who didn't reply gets on_mqtt=False, pushed OFFLINE, and the usual
offline alert (reused, not duplicated) so it's safe to confirm and delete.
Anyone who reappears gets on_mqtt flipped back on automatically.
"""

import logging

from django.db import transaction

from cameras.models import Camera, CameraStatus
from devices.models import Device, DeviceStatus
from monitoring.services.camera_monitor import update_camera_status
from monitoring.services.device_health import create_offline_alert, update_device_status
from mqtt import reconcile_state

logger = logging.getLogger("mqtt")


def start_reconcile_window() -> None:
    """Open a new reconciliation window (called right before (re)subscribing)."""

    reconcile_state.begin_cycle()
    logger.info("MQTT reconciliation window started.")


@transaction.atomic
def finish_reconcile_window() -> dict:
    """Close the window and apply it to every active device/camera.

    Returns how many of each were not seen.
    """

    seen_device_ids, seen_camera_ids = reconcile_state.snapshot_and_reset()

    missing_devices = 0
    missing_cameras = 0

    for device in Device.objects.filter(active=True):
        present = device.id in seen_device_ids

        if present:
            if not device.on_mqtt:
                device.on_mqtt = True
                device.save(update_fields=["on_mqtt", "updated_at"])
            continue

        missing_devices += 1

        if device.on_mqtt:
            device.on_mqtt = False
            device.save(update_fields=["on_mqtt", "updated_at"])

        if device.status != DeviceStatus.OFFLINE:
            update_device_status(device=device, new_status=DeviceStatus.OFFLINE)

        # idempotent -- just returns the existing alert if one's already active
        create_offline_alert(device)

    for camera in Camera.objects.filter(active=True):
        present = camera.id in seen_camera_ids

        if present:
            if not camera.on_mqtt:
                camera.on_mqtt = True
                camera.save(update_fields=["on_mqtt", "updated_at"])
            continue

        missing_cameras += 1

        if camera.on_mqtt:
            camera.on_mqtt = False
            camera.save(update_fields=["on_mqtt", "updated_at"])

        # update_camera_status already raises/reuses the offline alert itself
        update_camera_status(camera=camera, new_status=CameraStatus.OFFLINE)

    logger.info(
        "MQTT reconciliation finished: %s device(s) and %s camera(s) not seen on MQTT.",
        missing_devices,
        missing_cameras,
    )

    return {"missing_devices": missing_devices, "missing_cameras": missing_cameras}

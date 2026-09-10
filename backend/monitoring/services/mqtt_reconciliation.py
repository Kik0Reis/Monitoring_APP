"""
MQTT presence reconciliation.

The "Not on MQTT" badge (Devices/Cameras) is deliberately NOT time-based --
a device that just hasn't sent a heartbeat in a while is already covered
by the existing OFFLINE status/alert (see heartbeat_monitor.py). This
module answers a different question: has the broker itself stopped
knowing about this device/camera at all? That happens after e.g. deleting
a Country (which cascades and deletes everything under it) and MQTT
re-creating locations/devices from ongoing traffic -- some of the
resulting records may no longer correspond to anything the broker still
retains.

The subscriber (mqtt/subscriber.py) periodically forces the broker to
resend every retained message by unsubscribing and re-subscribing to the
wildcard topic, and records which devices/cameras replied within a short
window via mqtt/reconcile_state.py. This module closes that window and
applies the result: anything that didn't reply gets on_mqtt=False, is
pushed OFFLINE, and gets the same DEVICE_OFFLINE/CAMERA_OFFLINE alert
already used everywhere else (never duplicated here) -- so it can be
confirmed visually and deleted with confidence. Anything that reappears
has on_mqtt flipped back to True automatically.
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
    """
    Close the current reconciliation window and apply the result to every
    active device/camera. Returns how many of each were not seen.
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

        # Reuse the existing offline-alert logic (idempotent: it just
        # returns the existing active alert if there already is one).
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

        # update_camera_status already raises/reuses the CAMERA_OFFLINE
        # alert internally, so there's nothing else to do here.
        update_camera_status(camera=camera, new_status=CameraStatus.OFFLINE)

    logger.info(
        "MQTT reconciliation finished: %s device(s) and %s camera(s) not seen on MQTT.",
        missing_devices,
        missing_cameras,
    )

    return {"missing_devices": missing_devices, "missing_cameras": missing_cameras}

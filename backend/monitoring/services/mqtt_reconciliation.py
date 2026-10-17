# checks whether the broker still knows each device and camera, this is not a timeout check

import logging

from django.db import transaction

from cameras.models import Camera, CameraStatus
from devices.models import Device, DeviceStatus
from monitoring.services.camera_monitor import update_camera_status
from monitoring.services.device_health import create_offline_alert, update_device_status
from mqtt import reconcile_state

logger = logging.getLogger("mqtt")


# opens a new reconciliation window just before subscribing
def start_reconcile_window() -> None:
    reconcile_state.begin_cycle()
    logger.info("MQTT reconciliation window started.")


# closes the window and marks the devices and cameras that were not seen
@transaction.atomic
def finish_reconcile_window() -> dict:
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

        # returns the existing alert when one is already active
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

        # update_camera_status already creates or reuses the offline alert
        update_camera_status(camera=camera, new_status=CameraStatus.OFFLINE)

    logger.info(
        "MQTT reconciliation finished: %s device(s) and %s camera(s) not seen on MQTT.",
        missing_devices,
        missing_cameras,
    )

    return {"missing_devices": missing_devices, "missing_cameras": missing_cameras}

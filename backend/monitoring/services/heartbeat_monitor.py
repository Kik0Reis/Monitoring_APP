"""Checks for stale last_seen timestamps and flips devices/cameras offline.

MQTT processing updates last_seen every time a device/camera reports in --
this is the other half, catching the ones that stopped.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from cameras.models import Camera, CameraStatus
from devices.models import Device, DeviceStatus
from monitoring.services.camera_monitor import update_camera_status
from monitoring.services.device_health import create_offline_alert, update_device_status

DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 60


@transaction.atomic
def check_device_timeout(
    device: Device, timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS, now=None
) -> Device:
    """Mark one device OFFLINE (and raise an alert) once its heartbeat has expired."""

    if now is None:
        now = timezone.now()

    if device.last_seen is None:
        return device

    expires_at = device.last_seen + timedelta(seconds=timeout_seconds)

    if now <= expires_at:
        return device

    if device.status != DeviceStatus.OFFLINE:

        update_device_status(device=device, new_status=DeviceStatus.OFFLINE)

    create_offline_alert(device)

    return device


@transaction.atomic
def check_camera_timeout(
    camera: Camera, timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS, now=None
) -> Camera:
    """Mark a single camera OFFLINE if its last heartbeat has expired."""

    if now is None:
        now = timezone.now()

    if camera.last_seen is None:
        return camera

    expires_at = camera.last_seen + timedelta(seconds=timeout_seconds)

    if now <= expires_at:
        return camera

    if camera.status != CameraStatus.OFFLINE:

        update_camera_status(
            camera=camera, new_status=CameraStatus.OFFLINE, received_at=now
        )

    return camera


def check_all_device_timeouts(
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS, now=None
) -> int:
    """Sweep every active device for expired heartbeats; return how many are offline."""

    if now is None:
        now = timezone.now()

    offline_count = 0

    # only the columns we need -- devices can carry a large health_data/
    # component_statuses JSON blob we don't want on every sweep
    devices = Device.objects.filter(active=True).only(
        "id", "last_seen", "status", "name"
    )

    for device in devices:

        check_device_timeout(device=device, timeout_seconds=timeout_seconds, now=now)

        device.refresh_from_db(fields=["status"])

        if device.status == DeviceStatus.OFFLINE:
            offline_count += 1

    return offline_count


def check_all_camera_timeouts(
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS, now=None
) -> int:
    """Sweep every active camera for expired heartbeats; return how many are offline."""

    if now is None:
        now = timezone.now()

    offline_count = 0

    cameras = Camera.objects.filter(active=True).only(
        "id", "last_seen", "status", "name"
    )

    for camera in cameras:

        check_camera_timeout(camera=camera, timeout_seconds=timeout_seconds, now=now)

        camera.refresh_from_db(fields=["status"])

        if camera.status == CameraStatus.OFFLINE:
            offline_count += 1

    return offline_count


def check_all_heartbeats(
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS, now=None
) -> dict[str, int]:
    """Run the device and camera timeout sweeps together — what heartbeat_worker calls."""

    if now is None:
        now = timezone.now()

    devices_offline = check_all_device_timeouts(
        timeout_seconds=timeout_seconds, now=now
    )

    cameras_offline = check_all_camera_timeouts(
        timeout_seconds=timeout_seconds, now=now
    )

    return {"devices_offline": devices_offline, "cameras_offline": cameras_offline}

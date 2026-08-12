"""
Heartbeat timeout monitoring.

Checks both Edge devices and Cameras for expired heartbeats.

The MQTT layer is responsible for updating last_seen whenever valid
communication is received.

This service is responsible only for detecting when communication
has stopped.

Flow:

    MQTT message
        ↓
    Device.last_seen / Camera.last_seen
        ↓
    Heartbeat monitor
        ↓
    timeout exceeded?
        ↓
    ONLINE → OFFLINE
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from devices.models import Device, DeviceStatus
from cameras.models import Camera, CameraStatus

from monitoring.services.device_health import (
    create_offline_alert,
    update_device_status,
)

# If you have camera offline-alert functionality, import it here.
# from monitoring.services.camera_monitor import (
#     create_camera_offline_alert,
#     update_camera_status,
# )


DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 60


# ============================================================================
# Device heartbeat
# ============================================================================

@transaction.atomic
def check_device_timeout(
    device: Device,
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    now=None,
) -> Device:
    """
    Check whether an Edge device has stopped communicating.

    Devices with no last_seen remain UNKNOWN.

    Devices whose heartbeat has expired become OFFLINE.
    """

    if now is None:
        now = timezone.now()

    if device.last_seen is None:
        return device

    expires_at = (
        device.last_seen
        + timedelta(seconds=timeout_seconds)
    )

    if now <= expires_at:
        return device

    if device.status != DeviceStatus.OFFLINE:
        update_device_status(
            device=device,
            new_status=DeviceStatus.OFFLINE,
        )

    create_offline_alert(device)

    return device


# ============================================================================
# Camera heartbeat
# ============================================================================

@transaction.atomic
def check_camera_timeout(
    camera: Camera,
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    now=None,
) -> Camera:
    """
    Check whether a camera has stopped communicating.

    Cameras with no last_seen remain UNKNOWN.

    Cameras whose heartbeat has expired become OFFLINE.
    """

    if now is None:
        now = timezone.now()

    if camera.last_seen is None:
        return camera

    expires_at = (
        camera.last_seen
        + timedelta(seconds=timeout_seconds)
    )

    if now <= expires_at:
        return camera

    if camera.status != CameraStatus.OFFLINE:
        camera.status = CameraStatus.OFFLINE

        camera.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return camera


# ============================================================================
# Check all devices
# ============================================================================

def check_all_device_timeouts(
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    now=None,
) -> int:
    """
    Check all active Edge devices.

    Returns the number of devices currently OFFLINE.
    """

    if now is None:
        now = timezone.now()

    offline_count = 0

    devices = Device.objects.filter(
        active=True,
    )

    for device in devices:

        check_device_timeout(
            device=device,
            timeout_seconds=timeout_seconds,
            now=now,
        )

        device.refresh_from_db(
            fields=["status"],
        )

        if device.status == DeviceStatus.OFFLINE:
            offline_count += 1

    return offline_count


# ============================================================================
# Check all cameras
# ============================================================================

def check_all_camera_timeouts(
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    now=None,
) -> int:
    """
    Check all active cameras.

    Returns the number of cameras currently OFFLINE.
    """

    if now is None:
        now = timezone.now()

    offline_count = 0

    cameras = Camera.objects.filter(
        active=True,
    )

    for camera in cameras:

        check_camera_timeout(
            camera=camera,
            timeout_seconds=timeout_seconds,
            now=now,
        )

        camera.refresh_from_db(
            fields=["status"],
        )

        if camera.status == CameraStatus.OFFLINE:
            offline_count += 1

    return offline_count


# ============================================================================
# Check everything
# ============================================================================

def check_all_heartbeats(
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    now=None,
) -> dict[str, int]:
    """
    Check both Edge devices and Cameras.

    This is the function that the periodic monitoring job should call.
    """

    if now is None:
        now = timezone.now()

    devices_offline = check_all_device_timeouts(
        timeout_seconds=timeout_seconds,
        now=now,
    )

    cameras_offline = check_all_camera_timeouts(
        timeout_seconds=timeout_seconds,
        now=now,
    )

    return {
        "devices_offline": devices_offline,
        "cameras_offline": cameras_offline,
    }
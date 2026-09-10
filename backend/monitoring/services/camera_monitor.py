"""
Camera status and alert handling.

Mirrors monitoring/services/device_health.py, but for individual cameras
rather than the Edge device they're attached to.
"""

import logging
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from cameras.models import Camera, CameraStatus
from monitoring.models import AlertSeverity, CameraAlert, CameraAlertType
from mqtt import reconcile_state
from mqtt.provisioning import resolve_camera

logger = logging.getLogger(__name__)


@transaction.atomic
def update_camera_status(camera: Camera, new_status: str, received_at=None) -> Camera:
    """Change a camera's status, and keep its CAMERA_OFFLINE alert in sync with it."""

    if received_at is None:
        received_at = timezone.now()

    if new_status not in CameraStatus.values:
        raise ValueError(f"Invalid camera status: {new_status}")

    camera.status = new_status

    # Only update last_seen when the camera is actually communicating.
    if new_status == CameraStatus.ONLINE:
        camera.last_seen = received_at

    camera.save(update_fields=["status", "last_seen", "updated_at"])

    # Keep the "camera offline" alert in sync with the status we just set,
    # no matter which code path got us here (a timeout sweep, an explicit
    # "offline" in a bulk camera-status message, or a fresh detection
    # proving the camera is back).
    if new_status == CameraStatus.OFFLINE:
        create_camera_offline_alert(camera)
    elif new_status == CameraStatus.ONLINE:
        resolve_camera_offline_alerts(camera)

    return camera


def create_camera_offline_alert(camera: Camera) -> CameraAlert:
    """Raise a CAMERA_OFFLINE alert, or reuse the existing one if it's still active."""

    existing_alert = CameraAlert.objects.filter(
        camera=camera, alert_type=CameraAlertType.CAMERA_OFFLINE, active=True
    ).first()

    if existing_alert:
        return existing_alert

    return CameraAlert.objects.create(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        message=f"Camera '{camera.name}' is offline.",
    )


def resolve_camera_offline_alerts(camera: Camera) -> int:
    """Close out any active CAMERA_OFFLINE alert for this camera."""

    return CameraAlert.objects.filter(
        camera=camera, alert_type=CameraAlertType.CAMERA_OFFLINE, active=True
    ).update(active=False, resolved_at=timezone.now())


def get_camera(device, camera_identifier: str, channel: int) -> Camera | None:
    """Look up one specific active camera on a device, or None if it doesn't exist."""

    try:
        return Camera.objects.get(
            device=device,
            camera_identifier=camera_identifier,
            channel=channel,
            active=True,
        )

    except Camera.DoesNotExist:
        return None


def get_cameras_by_identifier(device, camera_identifier: str) -> list[Camera]:
    """
    Every active camera on this device with this identifier, across all
    channels — a bulk ".../cameras" status update doesn't say which
    channel it means, so a status update needs to apply to all of them.
    """

    return list(
        Camera.objects.filter(
            device=device, camera_identifier=camera_identifier, active=True
        )
    )


@transaction.atomic
def process_camera_status_list(
    device, payload: dict[str, Any], received_at=None
) -> int:
    """
    Process a bulk ".../cameras" status list — one MQTT message covering
    every camera attached to a device. Example payload:

        {
            "cameras": [
                {
                    "camera_id": "AXIS-B8A44F957EC7",
                    "name": "AXIS Camera - 100.69.131.11",
                    "latitude": 50.946661,
                    "longitude": -2.237372,
                    "status": "offline",
                    "seconds_since_last_seen": null
                }
            ]
        }

    Receiving this message proves the Edge device itself is online, but
    says nothing about whether any given camera is — each camera's status
    comes from its own entry in the payload, not from the fact the
    message arrived at all.
    """

    if received_at is None:
        received_at = timezone.now()

    cameras = payload.get("cameras", [])

    if not isinstance(cameras, list):
        return 0

    processed = 0

    for camera_data in cameras:

        if not isinstance(camera_data, dict):
            continue

        camera_identifier = camera_data.get("camera_id")

        if not camera_identifier:
            continue

        raw_status = str(camera_data.get("status", "unknown")).lower()

        if raw_status in {"online", "up", "healthy"}:
            camera_status = CameraStatus.ONLINE

        elif raw_status in {"offline", "down", "unhealthy"}:
            camera_status = CameraStatus.OFFLINE

        else:
            camera_status = CameraStatus.UNKNOWN

        matching_cameras = get_cameras_by_identifier(
            device=device, camera_identifier=camera_identifier
        )

        if not matching_cameras:

            # This device has never reported this camera_id before —
            # auto-create it (channel defaults to 1: this payload shape
            # doesn't carry channel information) instead of silently
            # dropping the status update.
            new_camera = resolve_camera(
                device=device,
                camera_identifier=camera_identifier,
                name=camera_data.get("name"),
            )

            matching_cameras = [new_camera]

        for camera in matching_cameras:

            update_camera_status(
                camera=camera, new_status=camera_status, received_at=received_at
            )

            # Appearing in this list -- even reported as offline -- proves
            # the device still knows about this camera and is reporting it
            # over MQTT, which is what "on_mqtt" tracks.
            reconcile_state.record_camera_seen(camera.id)

            processed += 1

    return processed


@transaction.atomic
def process_camera_info_list(
    device, payload: dict[str, Any], received_at=None
) -> int:
    """
    Process aiaction/.../info/cameras: identity info for every camera
    attached to this device (serial number, friendly name, GPS
    coordinates). Example payload:

        {
            "cameras": [
                {
                    "camera_id": "CAM-1",
                    "camera_serial_number": "B8A44F957EC7",
                    "name": "Test Camera",
                    "latitude": null,
                    "longitude": null
                }
            ]
        }

    Unlike the bulk status list, this never touches Camera.status -- it
    only fills in identity fields, and only overwrites name/serial_number
    while the camera is still pending_review, so a human's edits are
    never clobbered by MQTT traffic. Coordinates are always refreshed
    since they're telemetry, not something a human is expected to type in.
    """

    if received_at is None:
        received_at = timezone.now()

    cameras = payload.get("cameras", [])

    if not isinstance(cameras, list):
        return 0

    processed = 0

    for camera_data in cameras:

        if not isinstance(camera_data, dict):
            continue

        camera_identifier = camera_data.get("camera_id")

        if not camera_identifier:
            continue

        matching_cameras = get_cameras_by_identifier(
            device=device, camera_identifier=camera_identifier
        )

        if not matching_cameras:
            matching_cameras = [
                resolve_camera(
                    device=device,
                    camera_identifier=camera_identifier,
                    name=camera_data.get("name"),
                )
            ]

        name = camera_data.get("name")
        serial_number = camera_data.get("camera_serial_number")
        latitude = camera_data.get("latitude")
        longitude = camera_data.get("longitude")

        for camera in matching_cameras:

            update_fields = []

            if camera.pending_review:

                if name and camera.name != name:
                    camera.name = name
                    update_fields.append("name")

                if serial_number and camera.serial_number != serial_number:
                    camera.serial_number = serial_number
                    update_fields.append("serial_number")

            if latitude is not None and camera.latitude != latitude:
                camera.latitude = latitude
                update_fields.append("latitude")

            if longitude is not None and camera.longitude != longitude:
                camera.longitude = longitude
                update_fields.append("longitude")

            if update_fields:
                update_fields.append("updated_at")

                try:
                    camera.save(update_fields=update_fields)
                except IntegrityError:
                    # The reported name collided with another camera's
                    # name on this device (unique_camera_name_per_device)
                    # -- skip the rename rather than crash MQTT processing.
                    logger.warning(
                        "Could not rename camera %s to '%s' from MQTT info: "
                        "name already in use on this device.",
                        camera,
                        name,
                    )

            reconcile_state.record_camera_seen(camera.id)

            processed += 1

    return processed


def create_camera_alert(
    camera: Camera,
    alert_type: str,
    message: str,
    payload: dict[str, Any],
    severity: str = AlertSeverity.WARNING,
) -> CameraAlert:
    """Raise a camera alert of the given type, or reuse the existing active one."""

    existing_alert = CameraAlert.objects.filter(
        camera=camera, alert_type=alert_type, active=True
    ).first()

    if existing_alert:
        return existing_alert

    return CameraAlert.objects.create(
        camera=camera,
        alert_type=alert_type,
        severity=severity,
        message=message,
        raw_payload=payload,
    )


@transaction.atomic
def process_camera_alert(
    camera: Camera, payload: dict[str, Any], received_at=None
) -> CameraAlert:
    """
    Process a real-world detection reported by a camera (smoke, person,
    etc). Marks the camera online (it clearly is, since it just sent us
    something) and logs the detection as a CAMERA_ALERT.
    """

    if received_at is None:
        received_at = timezone.now()

    update_camera_status(
        camera=camera, new_status=CameraStatus.ONLINE, received_at=received_at
    )

    action_code = payload.get("action_code", "UNKNOWN")

    class_label = payload.get("class_label", "unknown")

    confidence = payload.get("confidence")

    message = f"Camera '{camera.name}' detected '{class_label}' (action={action_code}"

    if confidence is not None:
        message += f", confidence={confidence}"

    message += ")."

    return create_camera_alert(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_ALERT,
        message=message,
        payload=payload,
        severity=AlertSeverity.WARNING,
    )


@transaction.atomic
def process_camera_event(
    camera: Camera, payload: dict[str, Any], action_code: str, received_at=None
) -> CameraAlert | None:
    """
    Process a plain "event" message from a camera. Unlike an alert, an
    event isn't something worth surfacing on its own — it's only useful
    here as proof the camera is alive, so this just marks it online.
    """

    if received_at is None:
        received_at = timezone.now()

    update_camera_status(
        camera=camera, new_status=CameraStatus.ONLINE, received_at=received_at
    )

    return None


@transaction.atomic
def process_camera_error(
    camera: Camera, payload: dict[str, Any], received_at=None
) -> CameraAlert:
    """Process a camera-reported error: mark it online and raise a CAMERA_ERROR alert."""

    if received_at is None:
        received_at = timezone.now()

    update_camera_status(
        camera=camera, new_status=CameraStatus.ONLINE, received_at=received_at
    )

    error_message = payload.get(
        "message", payload.get("error", "Camera reported an error.")
    )

    return create_camera_alert(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_ERROR,
        message=f"Camera '{camera.name}' reported an error: {error_message}",
        payload=payload,
        severity=AlertSeverity.WARNING,
    )


@transaction.atomic
def process_camera_detection(
    camera: Camera, payload: dict[str, Any], received_at=None
) -> CameraAlert:
    """
    Process aiaction/.../detections/{camera_id}/{channel}: a specific
    camera detected something (smoke, person, etc). This is the direct
    replacement for the old per-camera "alert" topic -- the separate old
    "event"/"error" topics were folded into this single "detections"
    topic in the new scheme, so every message here is treated as a
    detection.
    """

    return process_camera_alert(camera=camera, payload=payload, received_at=received_at)

from typing import Any

from django.db import transaction
from django.utils import timezone

from cameras.models import Camera, CameraStatus
from monitoring.models import (
    AlertSeverity,
    CameraAlert,
    CameraAlertType,
)
from mqtt.provisioning import resolve_camera


@transaction.atomic
def update_camera_status(
    camera: Camera,
    new_status: str,
    received_at=None,
) -> Camera:

    if received_at is None:
        received_at = timezone.now()

    if new_status not in CameraStatus.values:
        raise ValueError(f"Invalid camera status: {new_status}")

    camera.status = new_status

    # Only update last_seen when the camera is actually communicating.
    if new_status == CameraStatus.ONLINE:
        camera.last_seen = received_at

    camera.save(
        update_fields=[
            "status",
            "last_seen",
            "updated_at",
        ]
    )

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
    existing_alert = CameraAlert.objects.filter(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_OFFLINE,
        active=True,
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
    return CameraAlert.objects.filter(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_OFFLINE,
        active=True,
    ).update(
        active=False,
        resolved_at=timezone.now(),
    )


def get_camera(
    device,
    camera_identifier: str,
    channel: int,
) -> Camera | None:

    try:
        return Camera.objects.get(
            device=device,
            camera_identifier=camera_identifier,
            channel=channel,
            active=True,
        )

    except Camera.DoesNotExist:
        return None


def get_cameras_by_identifier(
    device,
    camera_identifier: str,
) -> list[Camera]:

    return list(
        Camera.objects.filter(
            device=device,
            camera_identifier=camera_identifier,
            active=True,
        )
    )


@transaction.atomic
def process_camera_status_list(
    device,
    payload: dict[str, Any],
    received_at=None,
) -> int:
    """
    Process:

        aiaction/.../{device_id}/cameras

    Example payload:

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

    The MQTT message itself proves the Edge is communicating.

    It does NOT prove that every camera is online.

    Therefore camera statuses are taken from the payload.
    """

    if received_at is None:
        received_at = timezone.now()

    cameras = payload.get(
        "cameras",
        [],
    )

    if not isinstance(cameras, list):
        return 0

    processed = 0

    for camera_data in cameras:

        if not isinstance(camera_data, dict):
            continue

        camera_identifier = camera_data.get("camera_id")

        if not camera_identifier:
            continue

        raw_status = str(
            camera_data.get(
                "status",
                "unknown",
            )
        ).lower()

        if raw_status in {
            "online",
            "up",
            "healthy",
        }:
            camera_status = CameraStatus.ONLINE

        elif raw_status in {
            "offline",
            "down",
            "unhealthy",
        }:
            camera_status = CameraStatus.OFFLINE

        else:
            camera_status = CameraStatus.UNKNOWN

        matching_cameras = get_cameras_by_identifier(
            device=device,
            camera_identifier=camera_identifier,
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
                camera=camera,
                new_status=camera_status,
                received_at=received_at,
            )

            processed += 1

    return processed


def create_camera_alert(
    camera: Camera,
    alert_type: str,
    message: str,
    payload: dict[str, Any],
    severity: str = AlertSeverity.WARNING,
) -> CameraAlert:

    existing_alert = CameraAlert.objects.filter(
        camera=camera,
        alert_type=alert_type,
        active=True,
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
    camera: Camera,
    payload: dict[str, Any],
    received_at=None,
) -> CameraAlert:

    if received_at is None:
        received_at = timezone.now()

    update_camera_status(
        camera=camera,
        new_status=CameraStatus.ONLINE,
        received_at=received_at,
    )

    action_code = payload.get(
        "action_code",
        "UNKNOWN",
    )

    class_label = payload.get(
        "class_label",
        "unknown",
    )

    confidence = payload.get(
        "confidence",
    )

    message = (
        f"Camera '{camera.name}' detected " f"'{class_label}' " f"(action={action_code}"
    )

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
    camera: Camera,
    payload: dict[str, Any],
    action_code: str,
    received_at=None,
) -> CameraAlert | None:

    if received_at is None:
        received_at = timezone.now()

    update_camera_status(
        camera=camera,
        new_status=CameraStatus.ONLINE,
        received_at=received_at,
    )

    return None


@transaction.atomic
def process_camera_error(
    camera: Camera,
    payload: dict[str, Any],
    received_at=None,
) -> CameraAlert:

    if received_at is None:
        received_at = timezone.now()

    update_camera_status(
        camera=camera,
        new_status=CameraStatus.ONLINE,
        received_at=received_at,
    )

    error_message = payload.get(
        "message",
        payload.get(
            "error",
            "Camera reported an error.",
        ),
    )

    return create_camera_alert(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_ERROR,
        message=(f"Camera '{camera.name}' reported an error: " f"{error_message}"),
        payload=payload,
        severity=AlertSeverity.WARNING,
    )

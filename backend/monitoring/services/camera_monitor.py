"""Camera status and alert handling. Mirrors device_health.py, but per-camera."""

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
    """Set a camera's status and keep its CAMERA_OFFLINE alert in sync."""

    if received_at is None:
        received_at = timezone.now()

    if new_status not in CameraStatus.values:
        raise ValueError(f"Invalid camera status: {new_status}")

    camera.status = new_status

    # only bump last_seen when it's actually communicating
    if new_status == CameraStatus.ONLINE:
        camera.last_seen = received_at

    camera.save(update_fields=["status", "last_seen", "updated_at"])

    # keep the offline alert in sync no matter what triggered this call
    # (timeout sweep, a bulk status message, or a fresh detection)
    if new_status == CameraStatus.OFFLINE:
        create_camera_offline_alert(camera)
    elif new_status == CameraStatus.ONLINE:
        resolve_camera_offline_alerts(camera)

    return camera


def create_camera_offline_alert(camera: Camera) -> CameraAlert:
    """Raise a CAMERA_OFFLINE alert, reusing the active one if there is one.

    See device_health.create_offline_alert -- same "manual resolve
    actually sticks" behavior: if the most recent CAMERA_OFFLINE alert
    was manually resolved and the camera hasn't come back online since,
    this keeps it resolved instead of instantly re-raising it.
    """

    existing_alert = CameraAlert.objects.filter(
        camera=camera, alert_type=CameraAlertType.CAMERA_OFFLINE, active=True
    ).first()

    if existing_alert:
        return existing_alert

    last_alert = (
        CameraAlert.objects.filter(camera=camera, alert_type=CameraAlertType.CAMERA_OFFLINE)
        .order_by("-created_at")
        .first()
    )

    if last_alert and last_alert.manually_resolved_at:
        last_alert.last_seen_at = timezone.now()
        last_alert.save(update_fields=["last_seen_at"])
        return last_alert

    return CameraAlert.objects.create(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        message=f"Camera '{camera.name}' is offline.",
    )


def resolve_camera_offline_alerts(camera: Camera) -> int:
    """Close any active CAMERA_OFFLINE alert for this camera.

    Also clears manually_resolved_at, same reasoning as
    device_health.resolve_offline_alerts.
    """

    CameraAlert.objects.filter(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_OFFLINE,
        manually_resolved_at__isnull=False,
    ).update(manually_resolved_at=None)

    return CameraAlert.objects.filter(
        camera=camera, alert_type=CameraAlertType.CAMERA_OFFLINE, active=True
    ).update(active=False, resolved_at=timezone.now())


def get_camera(device, camera_identifier: str, channel: int) -> Camera | None:
    """Look up one active camera on a device by identifier + channel."""

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
    """All active cameras on this device with this identifier, across channels.

    A bulk ".../cameras" status update doesn't say which channel it means,
    so it has to apply to every channel that shares the identifier.
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
    """Process a bulk ".../cameras" status list covering every camera on a device.

    {"cameras": [{"camera_id": "AXIS-B8A4...", "name": "...", "status": "offline", ...}]}

    Receiving this proves the Edge device is online, but each camera's own
    status comes from its entry in the list, not from the message arriving.
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
            # first time this device has reported this camera_id, auto-create it
            # (channel defaults to 1, this payload shape carries no channel info)
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

            # showing up here at all -- even as offline -- proves the device
            # still reports this camera over MQTT, which is what on_mqtt tracks
            reconcile_state.record_camera_seen(camera.id)

            processed += 1

    return processed


@transaction.atomic
def process_camera_info_list(
    device, payload: dict[str, Any], received_at=None
) -> int:
    """Process aiaction/.../info/cameras: identity info (serial, name, GPS) per camera.

    {"cameras": [{"camera_id": "CAM-1", "camera_serial_number": "...", "name": "...", ...}]}

    Never touches Camera.status. name/serial_number are only overwritten
    while the camera is pending_review, so a human's edits aren't clobbered
    by MQTT traffic. Coordinates are always refreshed since they're telemetry.
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
                    # name collided with another camera on this device, skip the
                    # rename instead of crashing MQTT processing
                    logger.warning(
                        "Could not rename camera %s to '%s' from MQTT info: "
                        "name already in use on this device.",
                        camera,
                        name,
                    )

            reconcile_state.record_camera_seen(camera.id)
            processed += 1

    return processed


@transaction.atomic
def process_camera_license_list(
    device, payload: dict[str, Any], received_at=None
) -> int:
    """Process aiaction/.../info/licenses: per-camera license status.

    {"licenses": [{"camera_id": "AXIS-...", "camera_name": "...", "channel_number": 1,
                   "licensed": true, "status": true, "begin_date": "...",
                   "end_date": "...", "days_left": 366, "last_validation_ok": true,
                   "last_validation_error": null, "last_validation_at": "..."}]}

    Stored as-is on Camera.license_data. Unlike process_camera_info_list,
    this never auto-creates cameras -- a license entry (e.g. an unused
    "Test-1" slot) doesn't necessarily correspond to a real camera the
    device has actually reported yet, so unmatched entries are just
    skipped and logged.
    """

    if received_at is None:
        received_at = timezone.now()

    licenses = payload.get("licenses", [])

    if not isinstance(licenses, list):
        return 0

    processed = 0

    for license_entry in licenses:
        if not isinstance(license_entry, dict):
            continue

        camera_identifier = license_entry.get("camera_id")
        channel = license_entry.get("channel_number")

        if not camera_identifier or channel is None:
            continue

        camera = get_camera(
            device=device, camera_identifier=camera_identifier, channel=channel
        )

        if camera is None:
            logger.warning(
                "Received MQTT license info for unknown camera: "
                "device=%s camera=%s channel=%s",
                device,
                camera_identifier,
                channel,
            )
            continue

        camera.license_data = license_entry
        camera.save(update_fields=["license_data", "updated_at"])

        reconcile_state.record_camera_seen(camera.id)
        processed += 1

    return processed


def update_camera_component_health(
    device, source: str, component_payload: dict[str, Any]
) -> int:
    """Extract one component's per-camera breakdown and store it on the relevant Camera(s).

    detectorapi/detector/idmr payloads report a "cameras" dict keyed by
    "{camera_id}_ch{channel}":

        {"cameras": {"CAM-1_ch1": {"stage": "idle", "error": null}}}

    Not every component has this (edge-device doesn't), so missing/wrong-shaped
    "cameras" is just a no-op.
    """

    cameras_data = component_payload.get("cameras")

    if not isinstance(cameras_data, dict):
        return 0

    updated = 0

    for key, data in cameras_data.items():
        if not isinstance(data, dict) or "_ch" not in key:
            continue

        camera_identifier, _, channel_part = key.rpartition("_ch")

        if not camera_identifier or not channel_part.isdigit():
            continue

        camera = Camera.objects.filter(
            device=device, camera_identifier=camera_identifier, channel=int(channel_part)
        ).first()

        if camera is None:
            continue

        health_data = dict(camera.health_data or {})
        health_data[source] = data
        camera.health_data = health_data
        camera.save(update_fields=["health_data", "updated_at"])

        updated += 1

    return updated


@transaction.atomic
def process_camera_detection(
    camera: Camera, payload: dict[str, Any], received_at=None
) -> CameraAlert:
    """Process aiaction/.../detections/{camera_id}/{channel}: a real-world detection.

    Marks the camera online (it just sent us something) and logs a
    CAMERA_ALERT with what was detected.

    Unlike CAMERA_OFFLINE/CAMERA_ERROR (see create_camera_offline_alert),
    this always creates a NEW row instead of reusing an active one --
    detections are a chronological log of distinct events (each smoke/
    person/etc event matters on its own), not a "currently broken" state
    with one row to keep updating. Retention is time-based instead (see
    settings.DETECTION_RETENTION_DAYS and
    monitoring.services.retention.delete_old_detections).
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

    return CameraAlert.objects.create(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_ALERT,
        severity=AlertSeverity.WARNING,
        message=message,
        raw_payload=payload,
    )

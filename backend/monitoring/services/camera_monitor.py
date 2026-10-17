# updates the status and alerts of a camera, works like device_health but per camera

import logging
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from cameras.models import Camera, CameraStatus
from monitoring.models import AlertSeverity, CameraAlert, CameraAlertType
from mqtt import reconcile_state
from mqtt.provisioning import resolve_camera

logger = logging.getLogger(__name__)


# sets the camera status and keeps its offline alert in sync
@transaction.atomic
def update_camera_status(camera: Camera, new_status: str, received_at=None) -> Camera:
    if received_at is None:
        received_at = timezone.now()

    if new_status not in CameraStatus.values:
        raise ValueError(f"Invalid camera status: {new_status}")

    camera.status = new_status

    # only update last_seen when the camera is communicating
    if new_status == CameraStatus.ONLINE:
        camera.last_seen = received_at

    camera.save(update_fields=["status", "last_seen", "updated_at"])

    # keep the offline alert in sync whatever triggered this call
    if new_status == CameraStatus.OFFLINE:
        create_camera_offline_alert(camera)
    elif new_status == CameraStatus.ONLINE:
        resolve_camera_offline_alerts(camera)

    return camera


# creates a camera offline alert, or returns the one already active
def create_camera_offline_alert(camera: Camera) -> CameraAlert:
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


# closes the active offline alerts of a camera
def resolve_camera_offline_alerts(camera: Camera) -> int:
    CameraAlert.objects.filter(
        camera=camera,
        alert_type=CameraAlertType.CAMERA_OFFLINE,
        manually_resolved_at__isnull=False,
    ).update(manually_resolved_at=None)

    return CameraAlert.objects.filter(
        camera=camera, alert_type=CameraAlertType.CAMERA_OFFLINE, active=True
    ).update(active=False, resolved_at=timezone.now())


# finds one active camera of a device by identifier and channel
def get_camera(device, camera_identifier: str, channel: int) -> Camera | None:
    try:
        return Camera.objects.get(
            device=device,
            camera_identifier=camera_identifier,
            channel=channel,
            active=True,
        )
    except Camera.DoesNotExist:
        return None


# finds all active cameras of a device with this identifier, in any channel
def get_cameras_by_identifier(device, camera_identifier: str) -> list[Camera]:
    return list(
        Camera.objects.filter(
            device=device, camera_identifier=camera_identifier, active=True
        )
    )


# handles the cameras status list that covers every camera of a device
@transaction.atomic
def process_camera_status_list(
    device, payload: dict[str, Any], received_at=None
) -> int:
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
            # first time this camera is reported, create it (the payload has no channel, so use channel 1)
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

            # being listed, even as offline, proves the device still reports this camera
            reconcile_state.record_camera_seen(camera.id)

            processed += 1

    return processed


# handles the info/cameras message with the serial, name and gps of each camera
@transaction.atomic
def process_camera_info_list(
    device, payload: dict[str, Any], received_at=None
) -> int:
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
                    # the name belongs to another camera of this device, skip the rename instead of failing
                    logger.warning(
                        "Could not rename camera %s to '%s' from MQTT info: "
                        "name already in use on this device.",
                        camera,
                        name,
                    )

            reconcile_state.record_camera_seen(camera.id)
            processed += 1

    return processed


# handles the info/licenses message with the license status of each camera
@transaction.atomic
def process_camera_license_list(
    device, payload: dict[str, Any], received_at=None
) -> int:
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


# stores the per-camera breakdown of one component on the matching cameras
def update_camera_component_health(
    device, source: str, component_payload: dict[str, Any]
) -> int:
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


# handles a detection message and saves it as a camera alert
@transaction.atomic
def process_camera_detection(
    camera: Camera, payload: dict[str, Any], received_at=None
) -> CameraAlert:
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

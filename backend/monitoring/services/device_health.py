# updates the status, heartbeats, components and alerts of a device from its mqtt messages

import logging
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from devices.models import Device, DeviceStatus
from monitoring.models import (
    AlertSeverity,
    AlertType,
    DeviceAlert,
    DeviceHeartbeat,
    DeviceStatusHistory,
)

logger = logging.getLogger(__name__)

# component status strings that mean everything is fine, anything else is unhealthy
HEALTHY_COMPONENT_STATUSES = {"up", "online", "healthy"}


# returns True when a component status string means the component is fine
def is_component_healthy(status: str) -> bool:
    return str(status).lower() in HEALTHY_COMPONENT_STATUSES


# sets the device status and logs the change, only when it changed
@transaction.atomic
def update_device_status(device: Device, new_status: str) -> Device:
    if new_status not in DeviceStatus.values:
        raise ValueError(f"Invalid device status: {new_status}")

    old_status = device.status

    if old_status == new_status:
        return device

    device.status = new_status
    device.save(update_fields=["status", "updated_at"])

    DeviceStatusHistory.objects.create(
        device=device, old_status=old_status, new_status=new_status
    )

    return device


# marks the device as having just communicated
def update_last_seen(device: Device, received_at=None) -> Device:
    if received_at is None:
        received_at = timezone.now()

    device.last_seen = received_at
    device.save(update_fields=["last_seen", "updated_at"])

    return device


# saves a heartbeat row and refreshes the last_seen of the device
@transaction.atomic
def record_heartbeat(
    device: Device, payload: dict[str, Any], received_at=None
) -> DeviceHeartbeat:
    if received_at is None:
        received_at = timezone.now()

    heartbeat = DeviceHeartbeat.objects.create(
        device=device, received_at=received_at, raw_payload=payload
    )

    update_last_seen(device=device, received_at=received_at)

    return heartbeat


# creates a device offline alert, or returns the one already active
def create_offline_alert(device: Device) -> DeviceAlert:
    existing_alert = DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_OFFLINE, active=True
    ).first()

    if existing_alert:
        return existing_alert

    last_alert = (
        DeviceAlert.objects.filter(device=device, alert_type=AlertType.DEVICE_OFFLINE)
        .order_by("-created_at")
        .first()
    )

    if last_alert and last_alert.manually_resolved_at:
        last_alert.last_seen_at = timezone.now()
        last_alert.save(update_fields=["last_seen_at"])
        return last_alert

    return DeviceAlert.objects.create(
        device=device,
        alert_type=AlertType.DEVICE_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        message=f"Device '{device.name}' is offline.",
    )


# closes the active offline alerts of a device
def resolve_offline_alerts(device: Device) -> int:
    DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_OFFLINE,
        manually_resolved_at__isnull=False,
    ).update(manually_resolved_at=None)

    return DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_OFFLINE, active=True
    ).update(active=False, resolved_at=timezone.now())


# stores the status of one internal component (for example detectorapi) on the device
@transaction.atomic
def update_component_status(
    device: Device, component_name: str, payload: dict[str, Any]
) -> Device:
    if not component_name:
        raise ValueError("Component name cannot be empty.")

    if not isinstance(payload, dict):
        raise ValueError("Component status payload must be a dictionary.")

    component_statuses = dict(device.component_statuses or {})
    component_statuses[component_name] = payload
    device.component_statuses = component_statuses

    device.save(update_fields=["component_statuses", "updated_at"])

    return device


# creates a health alert naming the unhealthy components, or reuses the active one
def create_health_alert(
    device: Device, unhealthy_components: list[str], payload: dict[str, Any]
) -> DeviceAlert:
    message = (
        f"Device '{device.name}' has unhealthy components: "
        f"{', '.join(unhealthy_components)}."
    )

    existing_alert = DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_HEALTH, active=True
    ).first()

    if existing_alert:
        return existing_alert

    return DeviceAlert.objects.create(
        device=device,
        alert_type=AlertType.DEVICE_HEALTH,
        severity=AlertSeverity.WARNING,
        message=message,
        raw_payload=payload,
    )


# closes the active health alerts of a device
def resolve_health_alerts(device: Device) -> int:
    return DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_HEALTH, active=True
    ).update(active=False, resolved_at=timezone.now())


# handles a health/<source> mqtt message
@transaction.atomic
def process_device_status(
    device: Device,
    status: str,
    source: str | None = None,
    payload: dict[str, Any] | None = None,
    received_at=None,
) -> Device:
    if received_at is None:
        received_at = timezone.now()

    status = status.lower()

    if source == "edge-device":
        if status == "online":
            update_last_seen(device=device, received_at=received_at)
            update_device_status(device=device, new_status=DeviceStatus.ONLINE)
            resolve_offline_alerts(device)
            return device

        if status == "offline":
            update_device_status(device=device, new_status=DeviceStatus.OFFLINE)
            create_offline_alert(device)
            return device

        if status == "unknown":
            update_last_seen(device=device, received_at=received_at)
            update_device_status(device=device, new_status=DeviceStatus.UNKNOWN)
            return device

        raise ValueError(f"Invalid Edge status: {status}")

    # everything below is an internal component (detectorapi, detector, idmr, ...)
    component_payload = dict(payload or {})
    component_payload.setdefault("status", status)

    update_component_status(
        device=device, component_name=source or "unknown", payload=component_payload
    )

    # copy the per-camera breakdown of this component to the matching cameras
    from monitoring.services.camera_monitor import update_camera_component_health

    update_camera_component_health(
        device=device, source=source or "unknown", component_payload=component_payload
    )

    # a component report is also a sign of life, so the device is online
    update_last_seen(device=device, received_at=received_at)
    update_device_status(device=device, new_status=DeviceStatus.ONLINE)
    resolve_offline_alerts(device)

    if not is_component_healthy(status):
        create_health_alert(
            device=device,
            unhealthy_components=[source or "unknown"],
            payload=component_payload,
        )
    else:
        # a component came back healthy, check if all of them are healthy now
        process_component_health_alerts(device=device)

    return device


# checks every known component and creates or resolves the health alert
def process_component_health_alerts(device: Device) -> None:
    component_statuses = device.component_statuses or {}
    unhealthy_components = []

    for component_name, component in component_statuses.items():
        if not isinstance(component, dict):
            continue

        status = str(component.get("status", "")).lower()

        if not is_component_healthy(status):
            unhealthy_components.append(component_name)

    if unhealthy_components:
        create_health_alert(
            device=device,
            unhealthy_components=unhealthy_components,
            payload=component_statuses,
        )
    else:
        resolve_health_alerts(device)


# handles the info/edge-device message with the hardware and system info
@transaction.atomic
def process_device_info(device: Device, payload: dict[str, Any], received_at=None) -> Device:
    if received_at is None:
        received_at = timezone.now()

    update_fields = ["system_info", "updated_at"]
    device.system_info = payload

    real_serial = payload.get("device_id")

    if device.pending_review and real_serial and device.serial_number != real_serial:
        device.serial_number = real_serial
        update_fields.append("serial_number")

    try:
        device.save(update_fields=update_fields)
    except IntegrityError:
        # another device already has this serial number, keep the placeholder instead of failing
        logger.warning(
            "Could not set serial number '%s' on device %s from MQTT info: "
            "already in use by another device.",
            real_serial,
            device,
        )
        device.serial_number = Device.objects.get(pk=device.pk).serial_number
        device.save(update_fields=["system_info", "updated_at"])

    update_last_seen(device=device, received_at=received_at)

    if device.status == DeviceStatus.OFFLINE:
        update_device_status(device=device, new_status=DeviceStatus.ONLINE)
        resolve_offline_alerts(device)

    return device


# creates an error alert for a named issue, or reuses the active one
def create_device_issue_alert(
    device: Device, issue_name: str, payload: dict[str, Any]
) -> DeviceAlert:
    existing_alerts = DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_ERROR, active=True
    )

    for alert in existing_alerts:
        if alert.raw_payload.get("issue_name") == issue_name:
            alert.last_seen_at = timezone.now()
            alert.save(update_fields=["last_seen_at"])
            return alert

    stale_cutoff = timezone.now() - timezone.timedelta(hours=settings.ALERT_STALE_HOURS)

    recent_resolved_alerts = DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_ERROR,
        manually_resolved_at__isnull=False,
    ).order_by("-created_at")[:20]

    for alert in recent_resolved_alerts:
        if alert.raw_payload.get("issue_name") != issue_name:
            continue

        if alert.last_seen_at >= stale_cutoff:
            alert.last_seen_at = timezone.now()
            alert.save(update_fields=["last_seen_at"])
            return alert

        break

    message = (
        payload.get("message")
        or payload.get("description")
        or f"Device '{device.name}' reported issue: {issue_name}."
    )

    stored_payload = dict(payload)
    stored_payload["issue_name"] = issue_name

    return DeviceAlert.objects.create(
        device=device,
        alert_type=AlertType.DEVICE_ERROR,
        severity=AlertSeverity.WARNING,
        message=message,
        raw_payload=stored_payload,
    )


# handles an issues/<name> message, a problem reported by the edge
@transaction.atomic
def process_device_issue(
    device: Device, issue_name: str, payload: dict[str, Any], received_at=None
) -> DeviceAlert:
    if received_at is None:
        received_at = timezone.now()

    update_last_seen(device=device, received_at=received_at)

    if device.status == DeviceStatus.OFFLINE:
        update_device_status(device=device, new_status=DeviceStatus.ONLINE)
        resolve_offline_alerts(device)

    return create_device_issue_alert(device=device, issue_name=issue_name, payload=payload)


# handles the overall-health snapshot message, the edge-device entry is not shown as a component
@transaction.atomic
def process_overall_health(
    device: Device, payload: dict[str, Any], received_at=None
) -> DeviceHeartbeat:
    # imported here to keep the dependency one way, camera_monitor does not import this module
    from monitoring.services.camera_monitor import (
        process_camera_status_list,
        update_camera_component_health,
    )

    if received_at is None:
        received_at = timezone.now()

    heartbeat = record_heartbeat(device=device, payload=payload, received_at=received_at)

    # receiving a snapshot proves the edge is online
    update_device_status(device=device, new_status=DeviceStatus.ONLINE)
    resolve_offline_alerts(device)

    raw_components = payload.get("components", {})

    if not isinstance(raw_components, dict):
        raw_components = {}

    components = dict(raw_components)
    components.pop("edge-device", None)  # the edge-device entry is not shown as its own component
    cameras_component = components.pop("cameras", None)

    device.health_data = payload

    component_statuses = {}
    unhealthy_components = []

    for component_name, component in components.items():
        if not isinstance(component, dict):
            continue

        component_statuses[component_name] = component
        status = str(component.get("status", "")).lower()

        if not is_component_healthy(status):
            unhealthy_components.append(component_name)

        update_camera_component_health(
            device=device, source=component_name, component_payload=component
        )

    device.component_statuses = component_statuses
    device.save(update_fields=["health_data", "component_statuses", "updated_at"])

    if unhealthy_components:
        create_health_alert(
            device=device, unhealthy_components=unhealthy_components, payload=payload
        )
    else:
        resolve_health_alerts(device)

    if isinstance(cameras_component, dict):
        camera_list = cameras_component.get("cameras", [])

        if isinstance(camera_list, list):
            process_camera_status_list(
                device=device, payload={"cameras": camera_list}, received_at=received_at
            )

    return heartbeat

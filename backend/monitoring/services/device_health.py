"""Device status/health processing: online-offline-unknown + internal components.

Device.status is only ever ONLINE/OFFLINE/UNKNOWN. Internal components
(detectorapi, detector, idmr, ...) have their own status strings like "up"
or "down" -- those must never leak into Device.status.
"""

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

# component status strings that mean "all good", everything else counts as unhealthy
HEALTHY_COMPONENT_STATUSES = {"up", "online", "healthy"}


def is_component_healthy(status: str) -> bool:
    """True if a component's reported status string means it's fine."""

    return str(status).lower() in HEALTHY_COMPONENT_STATUSES


@transaction.atomic
def update_device_status(device: Device, new_status: str) -> Device:
    """Set a device's status and log the transition, only if it changed."""

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


def update_last_seen(device: Device, received_at=None) -> Device:
    """Stamp a device as having just communicated (or at received_at)."""

    if received_at is None:
        received_at = timezone.now()

    device.last_seen = received_at
    device.save(update_fields=["last_seen", "updated_at"])

    return device


@transaction.atomic
def record_heartbeat(
    device: Device, payload: dict[str, Any], received_at=None
) -> DeviceHeartbeat:
    """Log a heartbeat row and refresh the device's last_seen."""

    if received_at is None:
        received_at = timezone.now()

    heartbeat = DeviceHeartbeat.objects.create(
        device=device, received_at=received_at, raw_payload=payload
    )

    update_last_seen(device=device, received_at=received_at)

    return heartbeat


def create_offline_alert(device: Device) -> DeviceAlert:
    """Raise a DEVICE_OFFLINE alert, reusing the active one if there is one.

    If the most recent DEVICE_OFFLINE alert for this device was manually
    resolved (see monitoring.views.DeviceAlertResolveView) and the device
    hasn't actually come back online since, this is still the same
    ongoing outage -- so instead of raising a brand new active alert
    (which would make a manual resolve pointless, since the device is
    still offline on every reconcile pass), this just bumps last_seen_at
    on the resolved row and leaves it resolved. A real "back online"
    signal (resolve_offline_alerts) clears manually_resolved_at, so the
    *next* time it goes offline this raises a fresh alert as normal.
    """

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


def resolve_offline_alerts(device: Device) -> int:
    """Close any active DEVICE_OFFLINE alert for this device.

    Also clears manually_resolved_at on every DEVICE_OFFLINE alert for
    this device: a real "back online" signal proves whatever comes next
    is a genuinely new outage, not the same one a human already
    dismissed, so create_offline_alert() should raise a fresh alert next
    time rather than staying suppressed forever.
    """

    DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_OFFLINE,
        manually_resolved_at__isnull=False,
    ).update(manually_resolved_at=None)

    return DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_OFFLINE, active=True
    ).update(active=False, resolved_at=timezone.now())


@transaction.atomic
def update_component_status(
    device: Device, component_name: str, payload: dict[str, Any]
) -> Device:
    """Store one internal component's status (e.g. detectorapi -> up) on the device.

    Written to Device.component_statuses, never to Device.status.
    """

    if not component_name:
        raise ValueError("Component name cannot be empty.")

    if not isinstance(payload, dict):
        raise ValueError("Component status payload must be a dictionary.")

    component_statuses = dict(device.component_statuses or {})
    component_statuses[component_name] = payload
    device.component_statuses = component_statuses

    device.save(update_fields=["component_statuses", "updated_at"])

    return device


def create_health_alert(
    device: Device, unhealthy_components: list[str], payload: dict[str, Any]
) -> DeviceAlert:
    """Raise a DEVICE_HEALTH alert naming the unhealthy component(s), reusing an active one."""

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


def resolve_health_alerts(device: Device) -> int:
    """Close any active DEVICE_HEALTH alert for this device."""

    return DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_HEALTH, active=True
    ).update(active=False, resolved_at=timezone.now())


@transaction.atomic
def process_device_status(
    device: Device,
    status: str,
    source: str | None = None,
    payload: dict[str, Any] | None = None,
    received_at=None,
) -> Device:
    """Process a health/{source} MQTT message.

    source="edge-device" is the Edge's actual MQTT connection/LWT status
    (online/offline/unknown). Anything else is an internal component
    (detectorapi, detector, idmr, ...) and never touches Device.status.
    """

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

    # everything below here is an internal component (detectorapi, detector, idmr, ...)
    component_payload = dict(payload or {})
    component_payload.setdefault("status", status)

    update_component_status(
        device=device, component_name=source or "unknown", payload=component_payload
    )

    # pull this component's per-camera breakdown (if any) onto the relevant Camera
    from monitoring.services.camera_monitor import update_camera_component_health

    update_camera_component_health(
        device=device, source=source or "unknown", component_payload=component_payload
    )

    # a component report is still communication from the Edge, so it counts
    # as the device being online too
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
        # a component just came back healthy, re-check whether all of them are now
        process_component_health_alerts(device=device)

    return device


def process_component_health_alerts(device: Device) -> None:
    """Re-check every known component and raise/resolve the health alert accordingly."""

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


@transaction.atomic
def process_device_info(device: Device, payload: dict[str, Any], received_at=None) -> Device:
    """Process aiaction/.../info/edge-device: hardware/system info (OS, CPU, RAM, GPU, IP...).

    Stored as-is in Device.system_info. Its device_id is a real, stable
    hardware identifier, so while the device is still pending_review this
    swaps out the auto-generated "AUTO-..." serial number for it. Never
    touches name/serial_number once a human has confirmed the device.
    """

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
        # another device already has this serial number, keep the placeholder
        # instead of crashing MQTT processing
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


def create_device_issue_alert(
    device: Device, issue_name: str, payload: dict[str, Any]
) -> DeviceAlert:
    """Raise a DEVICE_ERROR alert for a named issue, reusing the active alert for it if one exists.

    Bumps last_seen_at on reuse -- this is how resolve_stale_alerts()
    (monitoring/services/retention.py) later knows the issue is still
    being reported, vs. having simply stopped without an explicit
    "resolved" message.

    If the most recent alert for this exact issue_name was manually
    resolved (see monitoring.views.DeviceAlertResolveView) and it's still
    within settings.ALERT_STALE_HOURS of last being reported, this is
    still the same occurrence -- same reasoning as create_offline_alert,
    a manual resolve would otherwise be undone by the very next MQTT
    message repeating the same issue. There's no explicit "issue cleared"
    signal for DEVICE_ERROR (unlike offline/health), so a gap longer than
    ALERT_STALE_HOURS between reports is what counts as "this stopped and
    came back", raising a fresh alert instead.
    """

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


@transaction.atomic
def process_device_issue(
    device: Device, issue_name: str, payload: dict[str, Any], received_at=None
) -> DeviceAlert:
    """Process aiaction/.../issues/{issue_name}: a named problem reported by the Edge."""

    if received_at is None:
        received_at = timezone.now()

    update_last_seen(device=device, received_at=received_at)

    if device.status == DeviceStatus.OFFLINE:
        update_device_status(device=device, new_status=DeviceStatus.ONLINE)
        resolve_offline_alerts(device)

    return create_device_issue_alert(device=device, issue_name=issue_name, payload=payload)


@transaction.atomic
def process_overall_health(
    device: Device, payload: dict[str, Any], received_at=None
) -> DeviceHeartbeat:
    """Process aiaction/.../health/overall-health: the combined snapshot message.

    Its "components" block nests the Edge's own status and the camera list
    alongside the usual detectorapi/detector/idmr statuses.

    - "edge-device" is dropped: it's just the online/offline status already
      shown by the device's status badge, keeping it would just duplicate that.
    - "cameras" is delegated to process_camera_status_list.
    - everything else is treated like process_device_status's per-component
      path, including extracting per-camera breakdowns via
      camera_monitor.update_camera_component_health.
    """

    # imported here, not at module level, to keep this one-directional
    # dependency (camera_monitor doesn't import this module) explicit
    from monitoring.services.camera_monitor import (
        process_camera_status_list,
        update_camera_component_health,
    )

    if received_at is None:
        received_at = timezone.now()

    heartbeat = record_heartbeat(device=device, payload=payload, received_at=received_at)

    # a snapshot arriving at all proves the Edge is online
    update_device_status(device=device, new_status=DeviceStatus.ONLINE)
    resolve_offline_alerts(device)

    raw_components = payload.get("components", {})

    if not isinstance(raw_components, dict):
        raw_components = {}

    components = dict(raw_components)
    components.pop("edge-device", None)  # see docstring, never shown as its own component
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

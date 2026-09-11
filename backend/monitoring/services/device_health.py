"""
Device health and status monitoring services.

The Edge device itself has:

    ONLINE
    OFFLINE
    UNKNOWN

Internal components have their own statuses:

    detectorapi
    detector
    idmr
    ...

MQTT component statuses such as "up" and "down" must NEVER be
stored in Device.status.
"""

import logging
from typing import Any

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

# Component-level status strings (as reported over MQTT) that count as
# "everything is fine". Anything else is treated as unhealthy.
HEALTHY_COMPONENT_STATUSES = {"up", "online", "healthy"}


def is_component_healthy(status: str) -> bool:
    """Whether a component's reported status string counts as "fine"."""

    return str(status).lower() in HEALTHY_COMPONENT_STATUSES


@transaction.atomic
def update_device_status(device: Device, new_status: str) -> Device:
    """Change a device's status and log the transition, if it actually changed."""

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
    """Stamp a device as having communicated just now (or at received_at)."""

    if received_at is None:
        received_at = timezone.now()

    device.last_seen = received_at

    device.save(update_fields=["last_seen", "updated_at"])

    return device


@transaction.atomic
def record_heartbeat(
    device: Device, payload: dict[str, Any], received_at=None
) -> DeviceHeartbeat:
    """Log a heartbeat row for this device and refresh its last_seen."""

    if received_at is None:
        received_at = timezone.now()

    heartbeat = DeviceHeartbeat.objects.create(
        device=device, received_at=received_at, raw_payload=payload
    )

    update_last_seen(device=device, received_at=received_at)

    return heartbeat


def create_offline_alert(device: Device) -> DeviceAlert:
    """Raise a DEVICE_OFFLINE alert, or reuse the existing one if it's still active."""

    existing_alert = DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_OFFLINE, active=True
    ).first()

    if existing_alert:
        return existing_alert

    return DeviceAlert.objects.create(
        device=device,
        alert_type=AlertType.DEVICE_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        message=f"Device '{device.name}' is offline.",
    )


def resolve_offline_alerts(device: Device) -> int:
    """Close out any active DEVICE_OFFLINE alert for this device."""

    return DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_OFFLINE, active=True
    ).update(active=False, resolved_at=timezone.now())


@transaction.atomic
def update_component_status(
    device: Device, component_name: str, payload: dict[str, Any]
) -> Device:
    """
    Store the status of an internal Edge component.

    Example:

        detectorapi -> up
        detector    -> up
        idmr        -> up

    These values are stored in Device.component_statuses.

    They do NOT change Device.status.
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
    """Close out any active DEVICE_HEALTH alert for this device."""

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
    """
    Process a health/{source} MQTT message.

    Important distinction:

        health/detectorapi
        health/detector
        health/idmr
        (or any other health/{component} topic)

    are component statuses.

        health/edge-device

    represents the actual Edge MQTT connection/LWT status.
    """

    if received_at is None:
        received_at = timezone.now()

    status = status.lower()

    # Actual Edge status
    #
    # health/edge-device

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

    # Internal component status
    #
    # detectorapi
    # detector
    # idmr

    component_payload = dict(payload or {})
    component_payload.setdefault("status", status)

    update_component_status(
        device=device, component_name=source or "unknown", payload=component_payload
    )

    # Extract this component's per-camera breakdown (if any) onto the
    # relevant Camera -- see camera_monitor.update_camera_component_health.
    from monitoring.services.camera_monitor import update_camera_component_health

    update_camera_component_health(
        device=device, source=source or "unknown", component_payload=component_payload
    )

    # A detectorapi status message is still communication from the Edge.
    # Therefore update last_seen and keep the Edge ONLINE.
    #
    # Same principle applies to detector/idmr.
    update_last_seen(device=device, received_at=received_at)

    update_device_status(device=device, new_status=DeviceStatus.ONLINE)

    resolve_offline_alerts(device)

    # Component unhealthy?
    if not is_component_healthy(status):

        create_health_alert(
            device=device,
            unhealthy_components=[source or "unknown"],
            payload=component_payload,
        )

    else:

        # If this message says the component is healthy, we can
        # re-evaluate the complete component state.
        process_component_health_alerts(device=device)

    return device


def process_component_health_alerts(device: Device) -> None:
    """
    Re-evaluate all known component statuses.

    If any component is unhealthy, keep a health alert active.

    If all known components are healthy, resolve the health alert.
    """

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
    """
    Process aiaction/.../info/edge-device: hardware/system info about the
    Edge box itself (OS, CPU, RAM, GPU, IP address, ...). Stored as-is in
    Device.system_info for display on the device detail page.

    Its "device_id" is a real, stable hardware identifier -- while the
    device is still pending_review, this replaces the auto-generated
    "AUTO-..." placeholder serial number with it, the same way camera
    identity fields are only auto-filled before a human confirms them.
    This never touches Device.name/serial_number after they have been
    confirmed by a human.

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
        # Another device already has this serial number (unlikely, but
        # possible with duplicate/misconfigured hardware) -- keep the
        # placeholder rather than crash MQTT processing.
        logger.warning(
            "Could not set serial number '%s' on device %s from MQTT info: "
            "already in use by another device.",
            real_serial,
            device,
        )
        device.serial_number = Device.objects.get(pk=device.pk).serial_number
        device.save(update_fields=["system_info", "updated_at"])


    update_last_seen(device=device, received_at=received_at)

    # Receiving system info is still communication from the Edge.
    if device.status == DeviceStatus.OFFLINE:
        update_device_status(device=device, new_status=DeviceStatus.ONLINE)
        resolve_offline_alerts(device)

    return device


def create_device_issue_alert(
    device: Device, issue_name: str, payload: dict[str, Any]
) -> DeviceAlert:
    """
    Raise a DEVICE_ERROR alert for a named issue reported on
    aiaction/.../issues/{issue_name}, reusing the existing active alert
    for that same issue_name instead of duplicating it.
    """

    existing_alerts = DeviceAlert.objects.filter(
        device=device, alert_type=AlertType.DEVICE_ERROR, active=True
    )

    for alert in existing_alerts:
        if alert.raw_payload.get("issue_name") == issue_name:
            return alert

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

    # An issue report is still communication from the Edge.
    if device.status == DeviceStatus.OFFLINE:
        update_device_status(device=device, new_status=DeviceStatus.ONLINE)
        resolve_offline_alerts(device)

    return create_device_issue_alert(device=device, issue_name=issue_name, payload=payload)


@transaction.atomic
def process_overall_health(
    device: Device, payload: dict[str, Any], received_at=None
) -> DeviceHeartbeat:
    """
    Process aiaction/.../health/overall-health: the combined snapshot that
    replaced the old plain "health" topic. Its "components" block nests
    the Edge's own status and the full camera list alongside the usual
    detectorapi/detector/idmr component statuses.

    - "edge-device" is discarded entirely: it's just the Edge's own
      online/offline status, which is already what Device.status/the
      status badge shows -- keeping it as its own "component" card would
      just be a confusing duplicate.
    - "cameras" is handled by reusing process_camera_status_list.
    - Every other component is treated like process_device_status's
      per-component path AND has its per-camera breakdown (if any)
      extracted onto the relevant Camera via
      camera_monitor.update_camera_component_health.

    """

    # Imported here (rather than at module level) to avoid a circular
    # import: camera_monitor.py doesn't import this module, but keeping
    # the import local makes that one-directional dependency explicit.
    from monitoring.services.camera_monitor import (
        process_camera_status_list,
        update_camera_component_health,
    )


    if received_at is None:
        received_at = timezone.now()

    heartbeat = record_heartbeat(device=device, payload=payload, received_at=received_at)

    # A snapshot arriving at all proves the Edge is communicating.
    update_device_status(device=device, new_status=DeviceStatus.ONLINE)

    resolve_offline_alerts(device)

    raw_components = payload.get("components", {})

    if not isinstance(raw_components, dict):
        raw_components = {}

    components = dict(raw_components)

    # Never displayed as its own component -- see docstring above.
    components.pop("edge-device", None)

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

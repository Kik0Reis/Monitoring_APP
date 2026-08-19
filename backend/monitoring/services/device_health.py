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

from typing import Any

from django.db import transaction
from django.utils import timezone

from devices.models import Device, DeviceStatus

from monitoring.models import (
    AlertSeverity,
    AlertType,
    DeviceAlert,
    DeviceHeartbeat,
    DeviceStatusHistory,
)


# ============================================================================
# Device status
# ============================================================================


@transaction.atomic
def update_device_status(
    device: Device,
    new_status: str,
) -> Device:

    if new_status not in DeviceStatus.values:
        raise ValueError(
            f"Invalid device status: {new_status}"
        )

    old_status = device.status

    if old_status == new_status:
        return device

    device.status = new_status

    device.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    DeviceStatusHistory.objects.create(
        device=device,
        old_status=old_status,
        new_status=new_status,
    )

    return device


# ============================================================================
# Last seen
# ============================================================================


def update_last_seen(
    device: Device,
    received_at=None,
) -> Device:

    if received_at is None:
        received_at = timezone.now()

    device.last_seen = received_at

    device.save(
        update_fields=[
            "last_seen",
            "updated_at",
        ]
    )

    return device


# ============================================================================
# Device heartbeat
# ============================================================================


@transaction.atomic
def record_heartbeat(
    device: Device,
    payload: dict[str, Any],
    received_at=None,
) -> DeviceHeartbeat:

    if received_at is None:
        received_at = timezone.now()

    heartbeat = DeviceHeartbeat.objects.create(
        device=device,
        received_at=received_at,
        raw_payload=payload,
    )

    update_last_seen(
        device=device,
        received_at=received_at,
    )

    return heartbeat


# ============================================================================
# Offline alert
# ============================================================================


def create_offline_alert(
    device: Device,
) -> DeviceAlert:

    existing_alert = DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_OFFLINE,
        active=True,
    ).first()

    if existing_alert:
        return existing_alert

    return DeviceAlert.objects.create(
        device=device,
        alert_type=AlertType.DEVICE_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        message=(
            f"Device '{device.name}' is offline."
        ),
    )


# ============================================================================
# Resolve offline alerts
# ============================================================================


def resolve_offline_alerts(
    device: Device,
) -> int:

    return DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_OFFLINE,
        active=True,
    ).update(
        active=False,
        resolved_at=timezone.now(),
    )


# ============================================================================
# Component status
# ============================================================================


@transaction.atomic
def update_component_status(
    device: Device,
    component_name: str,
    payload: dict[str, Any],
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
        raise ValueError(
            "Component name cannot be empty."
        )

    if not isinstance(payload, dict):
        raise ValueError(
            "Component status payload must be a dictionary."
        )

    component_statuses = dict(
        device.component_statuses or {}
    )

    component_statuses[component_name] = payload

    device.component_statuses = component_statuses

    device.save(
        update_fields=[
            "component_statuses",
            "updated_at",
        ]
    )

    return device


# ============================================================================
# Component health alert
# ============================================================================


def create_health_alert(
    device: Device,
    unhealthy_components: list[str],
    payload: dict[str, Any],
) -> DeviceAlert:

    message = (
        f"Device '{device.name}' has unhealthy components: "
        f"{', '.join(unhealthy_components)}."
    )

    existing_alert = DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_HEALTH,
        active=True,
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


def resolve_health_alerts(
    device: Device,
) -> int:

    return DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_HEALTH,
        active=True,
    ).update(
        active=False,
        resolved_at=timezone.now(),
    )


# ============================================================================
# Process Edge status
# ============================================================================


@transaction.atomic
def process_device_status(
    device: Device,
    status: str,
    source: str | None = None,
    payload: dict[str, Any] | None = None,
    received_at=None,
) -> Device:
    """
    Process a status/{source} MQTT message.

    Important distinction:

        status/detectorapi
        status/detector
        status/idmr

    are component statuses.

        status/aiaction-edge

    represents the actual Edge MQTT connection/LWT status.
    """

    if received_at is None:
        received_at = timezone.now()

    status = status.lower()

    # ========================================================================
    # Actual Edge status
    #
    # status/aiaction-edge
    # ========================================================================

    if source == "aiaction-edge":

        if status == "online":
            update_last_seen(
                device=device,
                received_at=received_at,
            )

            update_device_status(
                device=device,
                new_status=DeviceStatus.ONLINE,
            )

            resolve_offline_alerts(device)

            return device

        if status == "offline":
            update_device_status(
                device=device,
                new_status=DeviceStatus.OFFLINE,
            )

            create_offline_alert(device)

            return device

        if status == "unknown":
            update_last_seen(
                device=device,
                received_at=received_at,
            )

            update_device_status(
                device=device,
                new_status=DeviceStatus.UNKNOWN,
            )

            return device

        raise ValueError(
            f"Invalid Edge status: {status}"
        )

    # ========================================================================
    # Internal component status
    #
    # detectorapi
    # detector
    # idmr
    # ========================================================================

    component_payload = dict(payload or {})
    component_payload.setdefault(
        "status",
        status,
    )

    update_component_status(
        device=device,
        component_name=source or "unknown",
        payload=component_payload,
    )

    # A detectorapi status message is still communication from the Edge.
    # Therefore update last_seen and keep the Edge ONLINE.
    #
    # Same principle applies to detector/idmr.
    update_last_seen(
        device=device,
        received_at=received_at,
    )

    update_device_status(
        device=device,
        new_status=DeviceStatus.ONLINE,
    )

    resolve_offline_alerts(device)

    # Component unhealthy?
    if status not in {"up", "online", "healthy"}:

        create_health_alert(
            device=device,
            unhealthy_components=[
                source or "unknown",
            ],
            payload=component_payload,
        )

    else:

        # If this message says the component is healthy, we can
        # re-evaluate the complete component state.
        process_component_health_alerts(
            device=device,
        )

    return device


# ============================================================================
# Re-evaluate component health
# ============================================================================


def process_component_health_alerts(
    device: Device,
) -> None:
    """
    Re-evaluate all known component statuses.

    If any component is unhealthy, keep a health alert active.

    If all known components are healthy, resolve the health alert.
    """

    component_statuses = (
        device.component_statuses or {}
    )

    unhealthy_components = []

    for component_name, component in component_statuses.items():

        if not isinstance(component, dict):
            continue

        status = str(
            component.get("status", "")
        ).lower()

        if status not in {
            "up",
            "online",
            "healthy",
        }:
            unhealthy_components.append(
                component_name
            )

    if unhealthy_components:

        create_health_alert(
            device=device,
            unhealthy_components=unhealthy_components,
            payload=component_statuses,
        )

    else:

        resolve_health_alerts(device)


# ============================================================================
# Process complete health message
# ============================================================================


@transaction.atomic
def process_device_health(
    device: Device,
    payload: dict[str, Any],
    received_at=None,
) -> DeviceHeartbeat:

    if received_at is None:
        received_at = timezone.now()

    heartbeat = record_heartbeat(
        device=device,
        payload=payload,
        received_at=received_at,
    )

    # A health message proves the Edge is communicating.
    update_device_status(
        device=device,
        new_status=DeviceStatus.ONLINE,
    )

    resolve_offline_alerts(device)

    # Store complete health information.
    device.health_data = payload

    # ========================================================================
    # Extract component statuses
    # ========================================================================

    components = payload.get(
        "components",
        {},
    )

    if not isinstance(components, dict):
        components = {}

    component_statuses = {}

    unhealthy_components = []

    for component_name, component in components.items():

        if not isinstance(component, dict):
            continue

        component_statuses[component_name] = component

        status = str(
            component.get("status", "")
        ).lower()

        if status not in {
            "up",
            "online",
            "healthy",
        }:
            unhealthy_components.append(
                component_name
            )

    device.component_statuses = component_statuses

    device.save(
        update_fields=[
            "health_data",
            "component_statuses",
            "updated_at",
        ]
    )

    # ========================================================================
    # Health alerts
    # ========================================================================

    if unhealthy_components:

        create_health_alert(
            device=device,
            unhealthy_components=unhealthy_components,
            payload=payload,
        )

    else:

        resolve_health_alerts(device)

    return heartbeat
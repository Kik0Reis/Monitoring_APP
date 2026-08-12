"""
Device health and status monitoring services.

This module contains the business logic responsible for updating
device health based on information received from MQTT.

The MQTT layer should NOT contain this logic.

The expected flow is:

    MQTT
      ↓
    Parser
      ↓
    Device Health Service
      ↓
    Database


Responsibilities of this service:

- Update Device.last_seen
- Update Device.status
- Create DeviceStatusHistory records
- Create DeviceAlert records
- Resolve alerts when a device becomes healthy again

This service does not:
- connect to MQTT
- parse MQTT topics
- parse JSON
- expose API endpoints
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
    """
    Update the current status of a device.

    If the status actually changes, a DeviceStatusHistory record
    is created.

    Example:

        ONLINE -> OFFLINE

    creates:

        DeviceStatusHistory(
            old_status="ONLINE",
            new_status="OFFLINE",
        )

    If the device is already OFFLINE and we receive another OFFLINE
    message, a new history record is NOT created.
    """

    if new_status not in DeviceStatus.values:
        raise ValueError(
            f"Invalid device status: {new_status}"
        )

    old_status = device.status

    # Nothing changed.
    if old_status == new_status:
        return device

    device.status = new_status
    device.save(
        update_fields=["status", "updated_at"]
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
    """
    Update the device's last_seen timestamp.

    If received_at is not provided, the current UTC timestamp is used.
    """

    if received_at is None:
        received_at = timezone.now()

    device.last_seen = received_at

    device.save(
        update_fields=["last_seen", "updated_at"]
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
    """
    Store a heartbeat/health message.

    The complete MQTT payload is stored in raw_payload.

    Known metrics are extracted when available.

    This function also updates Device.last_seen.
    """

    if received_at is None:
        received_at = timezone.now()

    heartbeat = DeviceHeartbeat.objects.create(
        device=device,
        received_at=received_at,
        raw_payload=payload,
    )

    # Update the device's last known communication time.
    update_last_seen(
        device=device,
        received_at=received_at,
    )

    return heartbeat


# ============================================================================
# Device offline alert
# ============================================================================


def create_offline_alert(
    device: Device,
) -> DeviceAlert:
    """
    Create an offline alert for a device if one is not already active.

    This prevents the monitoring system from creating a new identical
    alert every time the offline condition is evaluated.
    """

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
# Resolve offline alert
# ============================================================================


def resolve_offline_alerts(
    device: Device,
) -> int:
    """
    Resolve all active offline alerts for a device.

    Returns the number of alerts that were resolved.
    """

    updated = DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_OFFLINE,
        active=True,
    ).update(
        active=False,
        resolved_at=timezone.now(),
    )

    return updated


# ============================================================================
# Process device status
# ============================================================================


@transaction.atomic
def process_device_status(
    device: Device,
    status: str,
    received_at=None,
) -> Device:
    """
    Process an incoming device status message.

    ONLINE:
        - update last_seen
        - set device ONLINE
        - resolve offline alerts

    OFFLINE:
        - set device OFFLINE
        - create offline alert

    UNKNOWN:
        - update last_seen
        - set device UNKNOWN
    """

    if received_at is None:
        received_at = timezone.now()

    # --------------------------------------------------------------
    # ONLINE
    # --------------------------------------------------------------

    if status == DeviceStatus.ONLINE:

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

    # --------------------------------------------------------------
    # OFFLINE
    # --------------------------------------------------------------

    if status == DeviceStatus.OFFLINE:

        # IMPORTANT:
        # Do NOT update last_seen here.
        #
        # An offline/LWT message tells us that the device went
        # offline. It is not a new heartbeat.

        update_device_status(
            device=device,
            new_status=DeviceStatus.OFFLINE,
        )

        create_offline_alert(device)

        return device

    # --------------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------------

    if status == DeviceStatus.UNKNOWN:

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
        f"Invalid device status: {status}"
    )


# ============================================================================
# Process health message
# ============================================================================


@transaction.atomic
def process_device_health(
    device: Device,
    payload: dict[str, Any],
    received_at=None,
) -> DeviceHeartbeat:
    """
    Process a device health message.

    A health message proves that the device is communicating with
    the monitoring platform.

    Therefore:

        Health message received
            ↓
        Device = ONLINE

    The individual components inside the health payload are evaluated
    separately.

    Example:

        detector = up
        idmr = down
        requests = up

    Result:

        Device.status = ONLINE

        DeviceAlert:
            type = DEVICE_HEALTH
            severity = WARNING

    The device should NOT be marked OFFLINE because an internal
    component is unhealthy.

    A device becomes OFFLINE when it stops communicating and the
    monitoring system determines that its heartbeat has expired.
    That offline/timeout logic will be implemented separately.
    """

    if received_at is None:
        received_at = timezone.now()

    # ------------------------------------------------------------------
    # Store the heartbeat
    # ------------------------------------------------------------------

    heartbeat = record_heartbeat(
        device=device,
        payload=payload,
        received_at=received_at,
    )

    # ------------------------------------------------------------------
    # Receiving a health message proves that the device is communicating.
    #
    # Therefore the device itself is ONLINE.
    # ------------------------------------------------------------------

    update_device_status(
        device=device,
        new_status=DeviceStatus.ONLINE,
    )

    resolve_offline_alerts(device)

    # ------------------------------------------------------------------
    # Extract component information
    # ------------------------------------------------------------------

    components = payload.get("components", {})

    if not isinstance(components, dict):
        return heartbeat

    unhealthy_components = []

    for component_name, component in components.items():

        if not isinstance(component, dict):
            continue

        component_status = component.get("status")

        if component_status != "up":
            unhealthy_components.append(
                component_name
            )

    # ------------------------------------------------------------------
    # All components are healthy.
    #
    # Resolve existing component-health alerts.
    # ------------------------------------------------------------------

    if not unhealthy_components:

        resolve_health_alerts(device)

        return heartbeat

    # ------------------------------------------------------------------
    # One or more components are unhealthy.
    #
    # The device remains ONLINE.
    #
    # Create a health alert so the dashboard can show the problem.
    # ------------------------------------------------------------------

    create_health_alert(
        device=device,
        unhealthy_components=unhealthy_components,
        payload=payload,
    )

    return heartbeat


# ============================================================================
# Device health alerts
# ============================================================================


def create_health_alert(
    device: Device,
    unhealthy_components: list[str],
    payload: dict[str, Any],
) -> DeviceAlert:
    """
    Create a health alert when one or more internal device components
    are unhealthy.

    The device itself remains ONLINE because it successfully sent
    the health message.

    If an identical active health alert already exists, it is reused
    instead of creating duplicates.
    """

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
    """
    Resolve active health alerts when the device reports that all
    components are healthy again.

    Returns the number of alerts that were resolved.
    """

    updated = DeviceAlert.objects.filter(
        device=device,
        alert_type=AlertType.DEVICE_HEALTH,
        active=True,
    ).update(
        active=False,
        resolved_at=timezone.now(),
    )

    return updated


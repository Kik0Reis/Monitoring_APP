"""
MQTT message processing service.

This module connects the MQTT parser with the monitoring services.

It does NOT:
- connect to the MQTT broker
- subscribe to topics
- parse MQTT topics itself

Its responsibility is:

    parsed MQTT message
            ↓
       find Device
            ↓
       call correct monitoring service
"""

from typing import Any

from django.utils import timezone

from devices.models import Device

from monitoring.services.device_health import (
    process_device_health,
    process_device_status,
)

from mqtt.parser import (
    MQTTParserError,
    parse_message,
)


# ============================================================================
# Device lookup
# ============================================================================


class MQTTDeviceNotFoundError(Exception):
    """
    Raised when an MQTT message references a device that does not exist.
    """

    pass


def get_device(device_id: str) -> Device:
    """
    Find a Device using its MQTT identifier.

    The MQTT device_id is matched against Device.mqtt_identifier.
    """

    try:
        return Device.objects.get(
            mqtt_identifier=device_id,
        )
    except Device.DoesNotExist as exc:
        raise MQTTDeviceNotFoundError(
            f"Device with MQTT identifier "
            f"'{device_id}' does not exist."
        ) from exc


# ============================================================================
# Status message
# ============================================================================


def process_status_message(
    device: Device,
    payload: dict[str, Any],
) -> Device:
    """
    Process an MQTT device status message.

    Expected payload:

        {
            "status": "online",
            "version": "1.0.0",
            "timestamp": "...",
            "source": "aiaction"
        }
    """

    status = payload.get("status")

    if status == "online":
        from devices.models import DeviceStatus

        device_status = DeviceStatus.ONLINE

    elif status == "offline":
        from devices.models import DeviceStatus

        device_status = DeviceStatus.OFFLINE

    else:
        raise MQTTParserError(
            f"Unsupported device status: {status}"
        )

    return process_device_status(
        device=device,
        status=device_status,
        received_at=timezone.now(),
    )


# ============================================================================
# Health message
# ============================================================================


def process_health_message(
    device: Device,
    payload: dict[str, Any],
) -> Device:
    """
    Process an MQTT device health message.

    The monitoring service is responsible for evaluating the health
    components.
    """

    process_device_health(
        device=device,
        payload=payload,
        received_at=timezone.now(),
    )

    return device


# ============================================================================
# Complete MQTT message
# ============================================================================


def process_mqtt_message(
    topic: str,
    payload: bytes | str | dict,
) -> Device | None:
    """
    Process a complete MQTT message.

    Current supported message types:

        status
        health

    Camera-level messages are parsed successfully but are not yet
    processed into monitoring records.

    That is intentional. We first establish reliable device health
    monitoring before adding camera-level alert/event persistence.
    """

    message = parse_message(
        topic=topic,
        payload=payload,
    )

    topic_data = message["topic"]
    message_payload = message["payload"]

    message_type = topic_data["message_type"]

    # ------------------------------------------------------------------
    # Find the corresponding Device.
    # ------------------------------------------------------------------

    device = get_device(
        device_id=topic_data["device_id"],
    )

    # ------------------------------------------------------------------
    # Device status
    # ------------------------------------------------------------------

    if message_type == "status":

        return process_status_message(
            device=device,
            payload=message_payload,
        )

    # ------------------------------------------------------------------
    # Device health
    # ------------------------------------------------------------------

    if message_type == "health":

        return process_health_message(
            device=device,
            payload=message_payload,
        )

    # ------------------------------------------------------------------
    # Camera-level messages
    #
    # These are parsed but not persisted yet.
    # ------------------------------------------------------------------

    if message_type in {
        "alert",
        "event",
        "error",
    }:
        return device

    raise MQTTParserError(
        f"Unsupported MQTT message type: {message_type}"
    )

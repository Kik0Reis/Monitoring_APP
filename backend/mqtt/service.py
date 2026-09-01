"""
MQTT message service.

This module bridges the MQTT layer and the monitoring layer:

1. Receive a raw MQTT topic and payload.
2. Parse the MQTT message.
3. Resolve (and auto-provision) the Edge device.
4. Resolve the Camera when the message is camera-specific.
5. Hand the message off to the right monitoring service.

It deliberately does NOT connect to MQTT, parse topics itself, or contain
any monitoring business logic — that all lives in mqtt/parser.py and
monitoring/services/*.
"""

import logging

from monitoring.services.camera_monitor import (
    get_camera,
    process_camera_alert,
    process_camera_error,
    process_camera_event,
    process_camera_status_list,
)
from monitoring.services.device_health import (
    process_device_health,
    process_device_status,
)
from mqtt.parser import MQTTParserError, parse_mqtt_message
from mqtt.provisioning import resolve_device

logger = logging.getLogger(__name__)

# Message types that operate on the Edge device itself.
DEVICE_MESSAGE_TYPES = {"status", "health", "cameras"}

# Message types that operate on an individual camera attached to a device.
CAMERA_MESSAGE_TYPES = {"alert", "event", "error"}


def process_mqtt_message(topic: str, payload: bytes | str | dict):
    """
    Entry point for every incoming MQTT message.

    Returns the Device or Camera that was updated, or None if the message
    was invalid, unsupported, or referred to something we couldn't resolve.
    """

    logger.info("Processing MQTT message: %s", topic)

    try:
        parsed_message = parse_mqtt_message(topic=topic, payload=payload)
    except MQTTParserError as exc:
        logger.warning("Invalid MQTT message: %s", exc)
        return None

    message_type = parsed_message["message_type"]

    # Devices are resolved via the full topic path, not a bare device_id
    # lookup — mqtt_identifier is only unique *within* a location, so two
    # different customers can legitimately both have a device called "01".
    # See mqtt/provisioning.py for the full rationale.
    device = resolve_device(
        country_code=parsed_message["country"],
        client_key=parsed_message["client"],
        installation_key=parsed_message["installation"],
        device_id=parsed_message["device_id"],
    )

    if device is None:
        return None

    logger.info(
        "MQTT Edge resolved: country=%s client=%s installation=%s "
        "mqtt_identifier=%s device=%s",
        parsed_message["country"],
        parsed_message["client"],
        parsed_message["installation"],
        parsed_message["device_id"],
        device,
    )

    if message_type in DEVICE_MESSAGE_TYPES:
        return _handle_device_message(message_type, device, parsed_message)

    if message_type in CAMERA_MESSAGE_TYPES:
        return _handle_camera_message(message_type, device, parsed_message, topic)

    logger.warning("Unsupported MQTT message type: %s", message_type)
    return None


def _handle_device_message(message_type, device, parsed_message):
    """Handle a message that targets the Edge device itself (not a camera)."""

    payload_data = parsed_message["payload"]

    if message_type == "status":
        status = payload_data.get("status")

        if status is None:
            logger.warning("MQTT status message does not contain 'status' field")
            return None

        try:
            device = process_device_status(
                device=device,
                status=str(status),
                source=parsed_message.get("source"),
                payload=payload_data,
            )
        except ValueError:
            logger.exception(
                "Invalid MQTT status received: source=%s status=%s",
                parsed_message.get("source"),
                status,
            )
            return None

        device.refresh_from_db()
        logger.info(
            "MQTT status processed: device=%s source=%s status=%s " "device_status=%s",
            device,
            parsed_message.get("source"),
            status,
            device.status,
        )
        return device

    if message_type == "health":
        process_device_health(device=device, payload=payload_data)
        device.refresh_from_db()
        logger.info("MQTT health processed: device=%s status=%s", device, device.status)
        return device

    # message_type == "cameras": a bulk status update for every camera
    # attached to this device, sent as a single MQTT message.
    processed = process_camera_status_list(device=device, payload=payload_data)
    device.refresh_from_db()
    logger.info(
        "MQTT camera status list processed: device=%s cameras=%s",
        device,
        processed,
    )
    return device


def _handle_camera_message(message_type, device, parsed_message, topic):
    """Handle a message that targets one specific camera (alert/event/error)."""

    camera_id = parsed_message.get("camera_id")
    channel = parsed_message.get("channel")

    if not camera_id or channel is None:
        logger.warning("Camera MQTT message is missing camera_id/channel: %s", topic)
        return None

    camera = get_camera(device=device, camera_identifier=camera_id, channel=channel)

    if camera is None:
        logger.warning(
            "Received MQTT message for unknown camera: "
            "device=%s camera=%s channel=%s",
            device,
            camera_id,
            channel,
        )
        return None

    logger.info(
        "MQTT camera resolved: device=%s camera=%s channel=%s",
        device,
        camera,
        channel,
    )

    payload_data = parsed_message["payload"]

    if message_type == "alert":
        alert = process_camera_alert(camera=camera, payload=payload_data)
        camera.refresh_from_db()
        logger.info(
            "Camera alert processed: camera=%s alert=%s status=%s",
            camera,
            alert,
            camera.status,
        )
        return camera

    if message_type == "event":
        action_code = parsed_message.get("action_code")
        process_camera_event(
            camera=camera, payload=payload_data, action_code=action_code
        )
        camera.refresh_from_db()
        logger.info(
            "Camera event processed: camera=%s action=%s status=%s",
            camera,
            action_code,
            camera.status,
        )
        return camera

    # message_type == "error"
    alert = process_camera_error(camera=camera, payload=payload_data)
    camera.refresh_from_db()
    logger.info(
        "Camera error processed: camera=%s alert=%s status=%s",
        camera,
        alert,
        camera.status,
    )
    return camera

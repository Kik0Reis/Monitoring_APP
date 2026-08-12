"""
MQTT message service.

This module bridges the MQTT layer and the monitoring layer.

Responsibilities:

1. Receive a raw MQTT topic and payload.
2. Parse the MQTT message.
3. Resolve the Edge device.
4. Resolve the Camera when the message is camera-level.
5. Route the message to the correct monitoring service.

This module does NOT:

- connect to MQTT
- parse MQTT topics itself
- implement monitoring business logic
- implement heartbeat timeout logic
"""

import logging

from devices.models import Device

from mqtt.parser import MQTTParserError, parse_mqtt_message

from monitoring.services.device_health import (
    process_device_health,
    process_device_status,
)

from monitoring.services.camera_monitor import (
    get_camera,
    process_camera_alert,
    process_camera_error,
    process_camera_event,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Edge lookup
# ============================================================================

def get_device(
    device_id: str,
) -> Device | None:
    """
    Resolve an MQTT device identifier to an active Edge device.

    MQTT device_id maps to Device.mqtt_identifier.
    """

    try:
        return Device.objects.get(
            mqtt_identifier=device_id,
            active=True,
            device_type="EDGE",
        )

    except Device.DoesNotExist:

        logger.warning(
            "Received MQTT message for unknown Edge device: %s",
            device_id,
        )

        return None


# ============================================================================
# MQTT message processing
# ============================================================================

def process_mqtt_message(
    topic: str,
    payload: bytes | str | dict,
):
    """
    Process one MQTT message.

    Flow:

        MQTT
          ↓
        Parser
          ↓
        Edge lookup
          ↓
        Message type
          │
          ├── status → Device monitoring
          ├── health → Device monitoring
          │
          └── camera message
                  ↓
              Camera lookup
                  ↓
              Camera monitoring
    """

    logger.info(
        "Processing MQTT message: %s",
        topic,
    )

    # ========================================================================
    # Parse
    # ========================================================================

    try:

        parsed_message = parse_mqtt_message(
            topic=topic,
            payload=payload,
        )

    except MQTTParserError as exc:

        logger.warning(
            "Invalid MQTT message: %s",
            exc,
        )

        return None

    message_type = parsed_message["message_type"]
    device_id = parsed_message["device_id"]
    payload_data = parsed_message["payload"]

    # ========================================================================
    # Resolve Edge
    # ========================================================================

    device = get_device(device_id)

    if device is None:
        return None

    logger.info(
        "MQTT Edge resolved: mqtt_identifier=%s device=%s",
        device_id,
        device,
    )

    # ========================================================================
    # DEVICE STATUS
    # ========================================================================

    if message_type == "status":

        status = payload_data.get("status")

        if not status:

            logger.warning(
                "Status MQTT message does not contain 'status': %s",
                topic,
            )

            return None

        try:

            device = process_device_status(
                device=device,
                status=status.upper(),
            )

        except ValueError:

            logger.exception(
                "Invalid device status received from MQTT: %s",
                status,
            )

            return None

        device.refresh_from_db()

        logger.info(
            "Device status processed: device=%s status=%s",
            device,
            device.status,
        )

        return device

    # ========================================================================
    # DEVICE HEALTH
    # ========================================================================

    if message_type == "health":

        process_device_health(
            device=device,
            payload=payload_data,
        )

        device.refresh_from_db()

        logger.info(
            "Device health processed: device=%s status=%s",
            device,
            device.status,
        )

        return device

    # ========================================================================
    # CAMERA MESSAGE VALIDATION
    # ========================================================================

    # At this point the only supported message types should be:
    #
    #   alert
    #   event
    #   error
    #
    # All of these require a camera.

    if message_type not in {
        "alert",
        "event",
        "error",
    }:

        logger.warning(
            "Unsupported MQTT message type: %s",
            message_type,
        )

        return None

    camera_id = parsed_message.get("camera_id")
    channel = parsed_message.get("channel")

    if not camera_id or channel is None:

        logger.warning(
            "Camera MQTT message is missing camera_id/channel: %s",
            topic,
        )

        return None

    # ========================================================================
    # Resolve Camera
    # ========================================================================

    camera = get_camera(
        device=device,
        camera_identifier=camera_id,
        channel=channel,
    )

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
        "MQTT camera resolved: "
        "device=%s camera=%s channel=%s",
        device,
        camera,
        channel,
    )

    # ========================================================================
    # CAMERA ALERT
    # ========================================================================

    if message_type == "alert":

        alert = process_camera_alert(
            camera=camera,
            payload=payload_data,
        )

        camera.refresh_from_db()

        logger.info(
            "Camera alert processed: "
            "camera=%s alert=%s status=%s",
            camera,
            alert,
            camera.status,
        )

        return camera

    # ========================================================================
    # CAMERA EVENT
    # ========================================================================

    if message_type == "event":

        process_camera_event(
            camera=camera,
            payload=payload_data,
            action_code=parsed_message.get("action_code"),
        )

        camera.refresh_from_db()

        logger.info(
            "Camera event processed: "
            "camera=%s action=%s status=%s",
            camera,
            parsed_message.get("action_code"),
            camera.status,
        )

        return camera

    # ========================================================================
    # CAMERA ERROR
    # ========================================================================

    if message_type == "error":

        alert = process_camera_error(
            camera=camera,
            payload=payload_data,
        )

        camera.refresh_from_db()

        logger.info(
            "Camera error processed: "
            "camera=%s alert=%s status=%s",
            camera,
            alert,
            camera.status,
        )

        return camera

    return None


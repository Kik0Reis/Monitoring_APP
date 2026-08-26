"""
MQTT message service.

This module bridges the MQTT layer and the monitoring layer.

Responsibilities:

1. Receive a raw MQTT topic and payload.
2. Parse the MQTT message.
3. Resolve the Edge device.
4. Resolve the Camera when necessary.
5. Route the message to the correct monitoring service.

This module does NOT:

- connect to MQTT
- parse MQTT topics itself
- implement monitoring business logic
- implement heartbeat timeout logic
"""

import logging

from mqtt.parser import (
    MQTTParserError,
    parse_mqtt_message,
)

from mqtt.provisioning import resolve_device

from monitoring.services.device_health import (
    process_device_health,
    process_device_status,
)

from monitoring.services.camera_monitor import (
    get_camera,
    process_camera_alert,
    process_camera_error,
    process_camera_event,
    process_camera_status_list,
)


logger = logging.getLogger(__name__)


# ============================================================================
# MQTT message processing
# ============================================================================


def process_mqtt_message(
    topic: str,
    payload: bytes | str | dict,
):

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
    country_code = parsed_message["country"]
    client_key = parsed_message["client"]
    installation_key = parsed_message["installation"]
    device_id = parsed_message["device_id"]
    payload_data = parsed_message["payload"]
    source = parsed_message.get("source")

    # ========================================================================
    # Resolve (and auto-provision, if needed) the Country/Customer/
    # Location/Device tree.
    #
    # Devices are resolved via the FULL topic path, not a bare device_id
    # lookup — mqtt_identifier is only unique *within* a location, so two
    # different customers can legitimately both have a device called "01".
    # See mqtt/provisioning.py for the full rationale.
    # ========================================================================

    device = resolve_device(
        country_code=country_code,
        client_key=client_key,
        installation_key=installation_key,
        device_id=device_id,
    )

    if device is None:
        return None

    logger.info(
        "MQTT Edge resolved: "
        "country=%s client=%s installation=%s mqtt_identifier=%s device=%s",
        country_code,
        client_key,
        installation_key,
        device_id,
        device,
    )

    # ========================================================================
    # DEVICE / COMPONENT STATUS
    # ========================================================================

    if message_type == "status":

        status = payload_data.get("status")

        if status is None:

            logger.warning(
                "MQTT status message does not contain 'status': %s",
                topic,
            )

            return None

        try:

            device = process_device_status(
                device=device,
                status=str(status),
                source=source,
                payload=payload_data,
            )

        except ValueError:

            logger.exception(
                "Invalid MQTT status received: "
                "source=%s status=%s",
                source,
                status,
            )

            return None

        device.refresh_from_db()

        logger.info(
            "MQTT status processed: "
            "device=%s source=%s status=%s "
            "device_status=%s",
            device,
            source,
            status,
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
            "MQTT health processed: "
            "device=%s status=%s",
            device,
            device.status,
        )

        return device

    # ========================================================================
    # CAMERA STATUS LIST
    # ========================================================================

    if message_type == "cameras":

        processed = process_camera_status_list(
            device=device,
            payload=payload_data,
        )

        device.refresh_from_db()

        logger.info(
            "MQTT camera status list processed: "
            "device=%s cameras=%s",
            device,
            processed,
        )

        return device

    # ========================================================================
    # CAMERA MESSAGE VALIDATION
    # ========================================================================

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

    camera_id = parsed_message.get(
        "camera_id"
    )

    channel = parsed_message.get(
        "channel"
    )

    if not camera_id or channel is None:

        logger.warning(
            "Camera MQTT message is missing "
            "camera_id/channel: %s",
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
            action_code=parsed_message.get(
                "action_code"
            ),
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
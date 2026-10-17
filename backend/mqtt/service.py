# connects the mqtt messages to the monitoring services

import logging

from monitoring.services.camera_monitor import (
    get_camera,
    process_camera_detection,
    process_camera_info_list,
    process_camera_license_list,
    process_camera_status_list,
)
from monitoring.services.device_health import (
    process_device_info,
    process_device_issue,
    process_device_status,
    process_overall_health,
)
from mqtt import reconcile_state
from mqtt.parser import MQTTParserError, parse_mqtt_message
from mqtt.provisioning import resolve_device

logger = logging.getLogger(__name__)

# message types that update the device itself
DEVICE_MESSAGE_TYPES = {
    "device_info",
    "camera_info",
    "camera_licenses",
    "overall_health",
    "health_cameras",
    "health_edge_device",
    "health_component",
    "issue",
}

# message types that belong to one camera of the device
CAMERA_MESSAGE_TYPES = {"detection"}


# handles one mqtt message and returns the updated device or camera, or None
def process_mqtt_message(topic: str, payload: bytes | str | dict):
    logger.info("Processing MQTT message: %s", topic)

    try:
        parsed_message = parse_mqtt_message(topic=topic, payload=payload)
    except MQTTParserError as exc:
        logger.warning("Invalid MQTT message: %s", exc)
        return None

    message_type = parsed_message["message_type"]

    # looked up by the full topic path because mqtt_identifier is only unique inside a location
    device = resolve_device(
        country_code=parsed_message["country"],
        client_key=parsed_message["client"],
        installation_key=parsed_message["installation"],
        device_id=parsed_message["device_id"],
    )

    if device is None:
        return None

    # any message proves the device is alive on mqtt, the reconciliation window uses this
    reconcile_state.record_device_seen(device.id)

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


# sends a device level message to the right handler
def _handle_device_message(message_type, device, parsed_message):
    payload_data = parsed_message["payload"]

    if message_type == "device_info":
        device = process_device_info(device=device, payload=payload_data)
        logger.info("MQTT device info processed: device=%s", device)
        return device

    if message_type == "camera_info":
        processed = process_camera_info_list(device=device, payload=payload_data)
        device.refresh_from_db()
        logger.info(
            "MQTT camera info processed: device=%s cameras=%s", device, processed
        )
        return device

    if message_type == "camera_licenses":
        processed = process_camera_license_list(device=device, payload=payload_data)
        device.refresh_from_db()
        logger.info(
            "MQTT camera license info processed: device=%s cameras=%s",
            device,
            processed,
        )
        return device

    if message_type == "overall_health":
        process_overall_health(device=device, payload=payload_data)
        device.refresh_from_db()
        logger.info(
            "MQTT overall health processed: device=%s status=%s", device, device.status
        )
        return device

    if message_type == "health_cameras":
        processed = process_camera_status_list(device=device, payload=payload_data)
        device.refresh_from_db()
        logger.info(
            "MQTT camera health list processed: device=%s cameras=%s",
            device,
            processed,
        )
        return device

    if message_type == "health_edge_device":
        status = payload_data.get("status")

        if status is None:
            logger.warning(
                "MQTT health/edge-device message does not contain 'status' field"
            )
            return None

        try:
            device = process_device_status(
                device=device,
                status=str(status),
                source="edge-device",
                payload=payload_data,
            )
        except ValueError:
            logger.exception(
                "Invalid MQTT edge-device status received: status=%s", status
            )
            return None

        device.refresh_from_db()
        logger.info(
            "MQTT edge-device health processed: device=%s status=%s device_status=%s",
            device,
            status,
            device.status,
        )
        return device

    if message_type == "health_component":
        source = parsed_message.get("source")
        status = payload_data.get("status")

        if status is None:
            logger.warning(
                "MQTT component health message does not contain 'status' field: %s",
                source,
            )
            return None

        try:
            device = process_device_status(
                device=device, status=str(status), source=source, payload=payload_data
            )
        except ValueError:
            logger.exception(
                "Invalid MQTT component status received: source=%s status=%s",
                source,
                status,
            )
            return None

        device.refresh_from_db()
        logger.info(
            "MQTT component health processed: device=%s source=%s status=%s "
            "device_status=%s",
            device,
            source,
            status,
            device.status,
        )
        return device

    # the only message type left is issue
    issue_name = parsed_message.get("issue_name")
    process_device_issue(device=device, issue_name=issue_name, payload=payload_data)
    device.refresh_from_db()
    logger.info("MQTT device issue processed: device=%s issue=%s", device, issue_name)
    return device


# sends a camera level message to the right handler
def _handle_camera_message(message_type, device, parsed_message, topic):
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
        "MQTT camera resolved: device=%s camera=%s channel=%s", device, camera, channel
    )

    reconcile_state.record_camera_seen(camera.id)

    payload_data = parsed_message["payload"]

    alert = process_camera_detection(camera=camera, payload=payload_data)
    camera.refresh_from_db()
    logger.info(
        "Camera detection processed: camera=%s alert=%s status=%s",
        camera,
        alert,
        camera.status,
    )
    return camera

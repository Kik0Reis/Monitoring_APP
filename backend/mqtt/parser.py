"""Turns raw MQTT topic/payload strings into plain dicts. No DB access here."""

import json
from typing import Any


class MQTTParserError(Exception):
    """Topic or payload didn't match a known shape."""


def parse_topic(topic: str) -> dict[str, Any]:
    """
    Break an aiaction/... topic into its parts and classify the message type.

    aiaction/{country}/{client}/{installation}/{device_id}/info/edge-device
    aiaction/{country}/{client}/{installation}/{device_id}/info/cameras
    aiaction/{country}/{client}/{installation}/{device_id}/info/licenses
    aiaction/{country}/{client}/{installation}/{device_id}/health/overall-health
    aiaction/{country}/{client}/{installation}/{device_id}/health/cameras
    aiaction/{country}/{client}/{installation}/{device_id}/health/edge-device
    aiaction/{country}/{client}/{installation}/{device_id}/health/{component}
    aiaction/{country}/{client}/{installation}/{device_id}/issues/{issue_name}
    aiaction/{country}/{client}/{installation}/{device_id}/detections/{camera_id}/{channel}
    """

    if not isinstance(topic, str) or not topic.strip():
        raise MQTTParserError("MQTT topic cannot be empty.")

    # publishers sometimes leave a trailing slash on, strip it before splitting
    cleaned_topic = topic.strip().rstrip("/")

    if not cleaned_topic:
        raise MQTTParserError("MQTT topic cannot be empty.")

    parts = cleaned_topic.split("/")

    if not parts or parts[0] != "aiaction":
        raise MQTTParserError(
            f"Unsupported MQTT topic namespace: {parts[0] if parts else ''}"
        )

    if len(parts) < 6:
        raise MQTTParserError(f"Invalid MQTT topic: {topic}")

    country = parts[1]
    client = parts[2]
    installation = parts[3]
    device_id = parts[4]
    category = parts[5]

    if not country:
        raise MQTTParserError("MQTT topic country cannot be empty.")

    if not client:
        raise MQTTParserError("MQTT topic client cannot be empty.")

    if not installation:
        raise MQTTParserError("MQTT topic installation cannot be empty.")

    if not device_id:
        raise MQTTParserError("MQTT topic device_id cannot be empty.")

    base = {
        "country": country,
        "client": client,
        "installation": installation,
        "device_id": device_id,
    }

    if category == "info" and len(parts) == 7 and parts[6] == "edge-device":
        return {"message_type": "device_info", **base}

    if category == "info" and len(parts) == 7 and parts[6] == "cameras":
        return {"message_type": "camera_info", **base}

    if category == "info" and len(parts) == 7 and parts[6] == "licenses":
        return {"message_type": "camera_licenses", **base}

    if category == "health" and len(parts) == 7:
        health_topic = parts[6]

        if not health_topic:
            raise MQTTParserError("MQTT health topic cannot be empty.")

        if health_topic == "overall-health":
            return {"message_type": "overall_health", **base}

        if health_topic == "cameras":
            return {"message_type": "health_cameras", **base}

        if health_topic == "edge-device":
            return {"message_type": "health_edge_device", **base}

        # anything else under health/ is a component reporting its own status
        # (detectorapi, detector, idmr, whatever gets added later)
        return {"message_type": "health_component", "source": health_topic, **base}

    if category == "issues" and len(parts) == 7:
        issue_name = parts[6]

        if not issue_name:
            raise MQTTParserError("MQTT issue name cannot be empty.")

        return {"message_type": "issue", "issue_name": issue_name, **base}

    if category == "detections" and len(parts) == 8:
        camera_id = parts[6]
        raw_channel = parts[7]

        if not camera_id:
            raise MQTTParserError("Camera ID cannot be empty.")

        channel_digits = (
            raw_channel[2:] if raw_channel.lower().startswith("ch") else raw_channel
        )

        if not channel_digits.isdigit():
            raise MQTTParserError(f"Invalid channel in MQTT topic: {raw_channel}")

        return {
            "message_type": "detection",
            "camera_id": camera_id,
            "channel": int(channel_digits),
            **base,
        }

    raise MQTTParserError(f"Unsupported MQTT topic structure: {topic}")


def parse_payload(payload: bytes | str | dict) -> dict[str, Any]:
    """Decode a payload (bytes, JSON string, or dict) into a dict."""

    if isinstance(payload, dict):
        return payload

    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MQTTParserError("MQTT payload is not valid UTF-8.") from exc

    if not isinstance(payload, str):
        raise MQTTParserError("MQTT payload must be bytes, string, or dictionary.")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise MQTTParserError("MQTT payload is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise MQTTParserError("MQTT payload must contain a JSON object.")

    return data


def parse_mqtt_message(topic: str, payload: bytes | str | dict) -> dict[str, Any]:
    """
    Combine parse_topic + parse_payload into the single dict service.py expects.
    Optional fields (camera_id, channel, source, issue_name) always default to
    None so callers don't need to check if a key exists.
    """

    parsed_topic = parse_topic(topic)
    parsed_payload = parse_payload(payload)

    parsed_message = {**parsed_topic, "payload": parsed_payload}

    parsed_message.setdefault("camera_id", None)
    parsed_message.setdefault("channel", None)
    parsed_message.setdefault("source", None)
    parsed_message.setdefault("issue_name", None)

    return parsed_message

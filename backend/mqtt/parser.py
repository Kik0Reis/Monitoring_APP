"""
MQTT topic and payload parser.

This module only understands the shape of MQTT messages — it doesn't
touch the database, update devices, create alerts, or connect to MQTT.
It turns a raw topic + payload into a plain dict that mqtt/service.py
knows what to do with.
"""

import json
from typing import Any


class MQTTParserError(Exception):
    """Raised when an MQTT topic or payload doesn't match what we expect."""


def parse_topic(topic: str) -> dict[str, Any]:
    """
    Parse an AiAction MQTT topic into its component parts.

    Supported shapes:

        aiaction/{country}/{client}/{installation}/{device_id}/status/{source}
        aiaction/{country}/{client}/{installation}/{device_id}/health
        aiaction/{country}/{client}/{installation}/{device_id}/cameras
        aiaction/.../{device_id}/{camera_id}/ch{channel}/alert
        aiaction/.../{device_id}/{camera_id}/ch{channel}/event/{action_code}
        aiaction/.../{device_id}/{camera_id}/ch{channel}/error
    """

    if not isinstance(topic, str) or not topic.strip():
        raise MQTTParserError("MQTT topic cannot be empty.")

    parts = topic.strip().split("/")

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

    if not country:
        raise MQTTParserError("MQTT topic country cannot be empty.")

    if not client:
        raise MQTTParserError("MQTT topic client cannot be empty.")

    if not installation:
        raise MQTTParserError("MQTT topic installation cannot be empty.")

    if not device_id:
        raise MQTTParserError("MQTT topic device_id cannot be empty.")

    # Device status: aiaction/.../{device_id}/status/{source}
    if len(parts) == 7 and parts[5] == "status":
        source = parts[6]

        if not source:
            raise MQTTParserError("MQTT status source cannot be empty.")

        return {
            "message_type": "status",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
            "source": source,
        }

    # Device health: aiaction/.../{device_id}/health
    if len(parts) == 6 and parts[5] == "health":
        return {
            "message_type": "health",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
        }

    # Bulk camera status list: aiaction/.../{device_id}/cameras
    if len(parts) == 6 and parts[5] == "cameras":
        return {
            "message_type": "cameras",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
        }

    # Everything left targets a specific camera, so it needs a camera_id
    # and a "ch{n}" channel segment.
    if len(parts) < 8:
        raise MQTTParserError(f"Invalid camera MQTT topic: {topic}")

    camera_id = parts[5]
    channel = parts[6]

    if not camera_id:
        raise MQTTParserError("Camera ID cannot be empty.")

    if not channel.startswith("ch"):
        raise MQTTParserError(f"Invalid channel in MQTT topic: {channel}")

    channel_number = channel[2:]

    if not channel_number.isdigit():
        raise MQTTParserError(f"Invalid channel number: {channel}")

    channel_number = int(channel_number)

    if len(parts) == 8 and parts[7] == "alert":
        return {
            "message_type": "alert",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
            "camera_id": camera_id,
            "channel": channel_number,
        }

    if len(parts) == 8 and parts[7] == "error":
        return {
            "message_type": "error",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
            "camera_id": camera_id,
            "channel": channel_number,
        }

    if len(parts) == 9 and parts[7] == "event":
        action_code = parts[8]

        if not action_code:
            raise MQTTParserError("MQTT event action_code cannot be empty.")

        return {
            "message_type": "event",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
            "camera_id": camera_id,
            "channel": channel_number,
            "action_code": action_code,
        }

    raise MQTTParserError(f"Unsupported MQTT topic structure: {topic}")


def parse_payload(payload: bytes | str | dict) -> dict[str, Any]:
    """Decode an MQTT payload (bytes, JSON string, or already a dict) to a dict."""

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
    Parse a raw MQTT topic + payload into one dict the service layer can
    use directly — topic fields merged with the payload, plus every
    optional field (camera_id, channel, source, action_code) defaulted to
    None so callers never have to guess whether a key is present.
    """

    parsed_topic = parse_topic(topic)
    parsed_payload = parse_payload(payload)

    parsed_message = {**parsed_topic, "payload": parsed_payload}

    parsed_message.setdefault("camera_id", None)
    parsed_message.setdefault("channel", None)
    parsed_message.setdefault("source", None)
    parsed_message.setdefault("action_code", None)

    return parsed_message

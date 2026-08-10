"""
MQTT topic and payload parser.

This module is responsible ONLY for understanding MQTT messages.

It does not:
- access the database
- update devices
- create alerts
- connect to MQTT
- contain monitoring business logic

The parser converts a raw MQTT topic + payload into a structured
Python dictionary that can be passed to the MQTT service layer.
"""

import json
from typing import Any


# ============================================================================
# Exceptions
# ============================================================================


class MQTTParserError(Exception):
    """
    Raised when an MQTT topic or payload cannot be parsed.
    """

    pass


# ============================================================================
# Topic parser
# ============================================================================


def parse_topic(topic: str) -> dict[str, Any]:
    """
    Parse an AiAction MQTT topic.

    Supported topic structures:

        aiaction/{country}/{client}/{installation}/{device_id}/status/{source}

        aiaction/{country}/{client}/{installation}/{device_id}/health

        aiaction/{country}/{client}/{installation}/{device_id}/
        {camera_id}/ch{channel}/alert

        aiaction/{country}/{client}/{installation}/{device_id}/
        {camera_id}/ch{channel}/event/{action_code}

        aiaction/{country}/{client}/{installation}/{device_id}/
        {camera_id}/ch{channel}/error

    Returns a dictionary containing the extracted information.

    Example:

        {
            "message_type": "health",
            "country": "pt",
            "client": "aitecserv",
            "installation": "office2",
            "device_id": "edge-01",
        }
    """

    if not topic:
        raise MQTTParserError(
            "MQTT topic cannot be empty."
        )

    parts = topic.split("/")

    if len(parts) < 6:
        raise MQTTParserError(
            f"Invalid MQTT topic: {topic}"
        )

    # ------------------------------------------------------------------
    # Every supported topic must begin with "aiaction".
    # ------------------------------------------------------------------

    if parts[0] != "aiaction":
        raise MQTTParserError(
            f"Unsupported MQTT topic namespace: {parts[0]}"
        )

    country = parts[1]
    client = parts[2]
    installation = parts[3]
    device_id = parts[4]

    # ------------------------------------------------------------------
    # Device status
    #
    # aiaction/{country}/{client}/{installation}/{device_id}/status/{source}
    # ------------------------------------------------------------------

    if len(parts) == 7 and parts[5] == "status":

        return {
            "message_type": "status",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
            "source": parts[6],
        }

    # ------------------------------------------------------------------
    # Device health
    #
    # aiaction/{country}/{client}/{installation}/{device_id}/health
    # ------------------------------------------------------------------

    if len(parts) == 6 and parts[5] == "health":

        return {
            "message_type": "health",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
        }

    # ------------------------------------------------------------------
    # Camera-level topics
    # ------------------------------------------------------------------

    if len(parts) < 8:
        raise MQTTParserError(
            f"Invalid camera MQTT topic: {topic}"
        )

    camera_id = parts[5]
    channel = parts[6]

    # Channel must have the expected "ch" prefix.
    if not channel.startswith("ch"):
        raise MQTTParserError(
            f"Invalid channel in MQTT topic: {channel}"
        )

    channel_number = channel[2:]

    if not channel_number.isdigit():
        raise MQTTParserError(
            f"Invalid channel number: {channel}"
        )

    # ------------------------------------------------------------------
    # Alert
    #
    # .../{camera_id}/ch{channel}/alert
    # ------------------------------------------------------------------

    if len(parts) == 8 and parts[7] == "alert":

        return {
            "message_type": "alert",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
            "camera_id": camera_id,
            "channel": int(channel_number),
        }

    # ------------------------------------------------------------------
    # Error
    #
    # .../{camera_id}/ch{channel}/error
    # ------------------------------------------------------------------

    if len(parts) == 8 and parts[7] == "error":

        return {
            "message_type": "error",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
            "camera_id": camera_id,
            "channel": int(channel_number),
        }

    # ------------------------------------------------------------------
    # Event
    #
    # .../{camera_id}/ch{channel}/event/{action_code}
    # ------------------------------------------------------------------

    if (
        len(parts) == 9
        and parts[7] == "event"
    ):

        return {
            "message_type": "event",
            "country": country,
            "client": client,
            "installation": installation,
            "device_id": device_id,
            "camera_id": camera_id,
            "channel": int(channel_number),
            "action_code": parts[8],
        }

    raise MQTTParserError(
        f"Unsupported MQTT topic structure: {topic}"
    )


# ============================================================================
# Payload parser
# ============================================================================


def parse_payload(payload: bytes | str | dict) -> dict[str, Any]:
    """
    Convert an MQTT payload into a Python dictionary.

    MQTT libraries normally provide payloads as bytes.

    For testing, accepting a dictionary is convenient as well.
    """

    if isinstance(payload, dict):
        return payload

    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MQTTParserError(
                "MQTT payload is not valid UTF-8."
            ) from exc

    if not isinstance(payload, str):
        raise MQTTParserError(
            "MQTT payload must be bytes, string, or dictionary."
        )

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise MQTTParserError(
            "MQTT payload is not valid JSON."
        ) from exc

    if not isinstance(data, dict):
        raise MQTTParserError(
            "MQTT payload must contain a JSON object."
        )

    return data


# ============================================================================
# Complete message parser
# ============================================================================


def parse_message(
    topic: str,
    payload: bytes | str | dict,
) -> dict[str, Any]:
    """
    Parse a complete MQTT message.

    Returns:

        {
            "topic": {...},
            "payload": {...},
        }

    The returned structure is intentionally independent from Django
    models and the database.
    """

    parsed_topic = parse_topic(topic)
    parsed_payload = parse_payload(payload)

    return {
        "topic": parsed_topic,
        "payload": parsed_payload,
    }


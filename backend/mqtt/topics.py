"""
MQTT topic definitions for the AiAction platform.

AiAction topics follow this structure:

    aiaction/{country}/{client}/{installation}/{device_id}/status/{source}

    aiaction/{country}/{client}/{installation}/{device_id}/health

    aiaction/{country}/{client}/{installation}/{device_id}/{camera_id}/ch{channel}/alert

    aiaction/{country}/{client}/{installation}/{device_id}/{camera_id}/ch{channel}/event/{action_code}

    aiaction/{country}/{client}/{installation}/{device_id}/{camera_id}/ch{channel}/error
"""


# ---------------------------------------------------------------------------
# MQTT topic prefix
# ---------------------------------------------------------------------------

AIACTION_TOPIC_PREFIX = "aiaction"


# ---------------------------------------------------------------------------
# Device-level topics
# ---------------------------------------------------------------------------

# Device status / LWT topic.
#
# Example:
#
# aiaction/pt/aitecserv/office2/edge-01/status/aiaction-edge
#
# The "+" wildcard represents one topic level.
DEVICE_STATUS_TOPIC = (
    f"{AIACTION_TOPIC_PREFIX}/+"
    "/+/+/+/status/+"
)


# Device health topic.
#
# Example:
#
# aiaction/pt/aitecserv/office2/edge-01/health
DEVICE_HEALTH_TOPIC = (
    f"{AIACTION_TOPIC_PREFIX}/+"
    "/+/+/+/health"
)


# ---------------------------------------------------------------------------
# Camera-level topics
# ---------------------------------------------------------------------------

# Camera alert topic.
#
# Example:
#
# aiaction/pt/aitecserv/office2/edge-01/"
# "AXIS-B8A44F957EC7/ch1/alert"
CAMERA_ALERT_TOPIC = (
    f"{AIACTION_TOPIC_PREFIX}/+"
    "/+/+/+/"
    "+/ch+/alert"
)


# Camera event topic.
#
# Example:
#
# aiaction/pt/aitecserv/office2/edge-01/"
# "AXIS-B8A44F957EC7/ch1/event/HighProbFireDetected"
CAMERA_EVENT_TOPIC = (
    f"{AIACTION_TOPIC_PREFIX}/+"
    "/+/+/+/"
    "+/ch+/event/+"
)


# Camera error topic.
#
# Example:
#
# aiaction/pt/aitecserv/office2/edge-01/"
# "AXIS-B8A44F957EC7/ch1/error"
CAMERA_ERROR_TOPIC = (
    f"{AIACTION_TOPIC_PREFIX}/+"
    "/+/+/+/"
    "+/ch+/error"
)


# ---------------------------------------------------------------------------
# Subscription groups
# ---------------------------------------------------------------------------

# Topics required by the backend monitoring service.
#
# This allows the MQTT subscriber to subscribe to all AiAction
# message groups in one place.
AIACTION_SUBSCRIPTION_TOPICS = (
    (DEVICE_STATUS_TOPIC, 1),
    (DEVICE_HEALTH_TOPIC, 1),
    (CAMERA_ALERT_TOPIC, 2),
    (CAMERA_EVENT_TOPIC, 0),
    (CAMERA_ERROR_TOPIC, 0),
)


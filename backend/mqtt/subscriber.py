"""
MQTT subscriber.

Only responsible for connecting to the broker and receiving messages.
Topic/payload parsing, device updates, and alerting all live elsewhere
(see mqtt/service.py) — this class just hands raw messages off to it.
"""

import logging

import paho.mqtt.client as mqtt
from django.conf import settings

from mqtt.service import process_mqtt_message

logger = logging.getLogger(__name__)


class MQTTSubscriber:
    """MQTT subscriber for the AiAction MQTT namespace (topic: aiaction/#)."""

    def __init__(self):
        self.host = settings.MQTT_HOST
        self.port = settings.MQTT_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD
        self.topic = "aiaction/#"

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="monitoring-app-subscriber",
        )

        if self.username:
            self.client.username_pw_set(username=self.username, password=self.password)

        if settings.MQTT_TLS:
            self.client.tls_set()

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Subscribe to our topic once the broker connection is established."""

        logger.info("MQTT connection result: %s", reason_code)

        if reason_code != 0:
            logger.error("Failed to connect to EMQX Cloud. Reason: %s", reason_code)
            return

        logger.info("Connected to EMQX Cloud: %s:%s", self.host, self.port)

        result, _message_id = client.subscribe(self.topic, qos=1)

        if result == mqtt.MQTT_ERR_SUCCESS:
            logger.info("Subscribed successfully to: %s", self.topic)
        else:
            logger.error("Failed to subscribe to %s. Error: %s", self.topic, result)

    def on_message(self, client, userdata, message):
        """
        Hand a raw MQTT message off to the service layer.

        Wrapped in a broad try/except on purpose: one malformed or
        unexpected message must never take down this long-running
        subscriber process.
        """

        logger.info("MQTT message received. Topic: %s", message.topic)

        try:
            process_mqtt_message(topic=message.topic, payload=message.payload)
        except Exception:
            logger.exception("Error processing MQTT message: %s", message.topic)

    def on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties
    ):
        logger.warning("Disconnected from EMQX Cloud. Reason: %s", reason_code)

    def start(self):
        """Connect to the broker and block forever, processing messages."""

        logger.info("Starting MQTT subscriber...")
        logger.info("Connecting to EMQX Cloud %s:%s", self.host, self.port)

        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_forever()

    def stop(self):
        logger.info("Stopping MQTT subscriber...")
        self.client.disconnect()

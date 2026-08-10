"""
MQTT subscriber.

This module is responsible only for communicating with the MQTT broker.

Responsibilities:

    1. Connect to the MQTT broker.
    2. Subscribe to the AiAction topic namespace.
    3. Receive MQTT messages.
    4. Pass messages to the MQTT service.

It does NOT:

    - parse topics
    - parse JSON
    - update devices
    - create alerts
    - contain health logic

Those responsibilities belong to parser.py and service.py.
"""

import logging

import paho.mqtt.client as mqtt
from django.conf import settings

from mqtt.service import process_mqtt_message


# ============================================================================
# Logger
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# MQTT configuration
# ============================================================================

MQTT_TOPIC = "aiaction/#"


# ============================================================================
# Subscriber
# ============================================================================


class MQTTSubscriber:
    """
    MQTT subscriber responsible for receiving AiAction messages.
    """

    def __init__(self):
        """
        Initialize the MQTT client.

        Broker configuration comes from Django settings/environment
        variables.
        """

        self.host = settings.MQTT_HOST
        self.port = settings.MQTT_PORT

        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="monitoring-backend",
        )

        # --------------------------------------------------------------
        # Authentication
        # --------------------------------------------------------------

        if self.username:
            self.client.username_pw_set(
                username=self.username,
                password=self.password,
            )

        # --------------------------------------------------------------
        # MQTT callbacks
        # --------------------------------------------------------------

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    # ========================================================================
    # Connection
    # ========================================================================

    def on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ):
        """
        Called when the MQTT client connects to the broker.
        """

        if reason_code == 0:

            logger.info(
                "Connected to MQTT broker %s:%s",
                self.host,
                self.port,
            )

            # ----------------------------------------------------------
            # Subscribe to all AiAction messages.
            #
            # The parser will determine what type of message it is.
            # ----------------------------------------------------------

            result, mid = client.subscribe(
                MQTT_TOPIC,
                qos=1,
            )

            if result == mqtt.MQTT_ERR_SUCCESS:

                logger.info(
                    "Subscribed to MQTT topic: %s",
                    MQTT_TOPIC,
                )

            else:

                logger.error(
                    "Failed to subscribe to MQTT topic %s. "
                    "Error code: %s",
                    MQTT_TOPIC,
                    result,
                )

        else:

            logger.error(
                "Failed to connect to MQTT broker. "
                "Reason code: %s",
                reason_code,
            )

    # ========================================================================
    # Message received
    # ========================================================================

    def on_message(
        self,
        client,
        userdata,
        message,
    ):
        """
        Called whenever an MQTT message is received.

        The MQTT payload is passed directly to the MQTT service.

        The subscriber does not interpret the message.
        """

        logger.info(
            "MQTT message received: topic=%s",
            message.topic,
        )

        try:

            process_mqtt_message(
                topic=message.topic,
                payload=message.payload,
            )

        except Exception:
            """
            Never allow an exception from one MQTT message to kill
            the subscriber.

            The error is logged and the subscriber continues receiving
            future messages.
            """

            logger.exception(
                "Error processing MQTT message: %s",
                message.topic,
            )

    # ========================================================================
    # Disconnect
    # ========================================================================

    def on_disconnect(
        self,
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ):
        """
        Called when the MQTT client disconnects.
        """

        logger.warning(
            "Disconnected from MQTT broker. "
            "Reason code: %s",
            reason_code,
        )

    # ========================================================================
    # Start
    # ========================================================================

    def start(self):
        """
        Connect to the MQTT broker and start the MQTT network loop.
        """

        logger.info(
            "Connecting to MQTT broker %s:%s",
            self.host,
            self.port,
        )

        self.client.connect(
            self.host,
            self.port,
            keepalive=60,
        )

        # --------------------------------------------------------------
        # loop_forever() blocks this process and continuously handles
        # MQTT network traffic.
        # --------------------------------------------------------------

        self.client.loop_forever()

    # ========================================================================
    # Stop
    # ========================================================================

    def stop(self):
        """
        Stop the MQTT client cleanly.
        """

        logger.info(
            "Stopping MQTT subscriber."
        )

        self.client.disconnect()


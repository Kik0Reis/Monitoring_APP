"""
MQTT subscriber.

Responsible only for connecting to EMQX Cloud and receiving MQTT messages.

This module does not:
    - parse topics
    - parse JSON
    - update devices
    - create alerts
    - contain health logic

Those responsibilities will be handled by other MQTT/monitoring modules.
"""

import logging

import paho.mqtt.client as mqtt
from django.conf import settings
from mqtt.service import process_mqtt_message

logger = logging.getLogger(__name__)


class MQTTSubscriber:
    """
    MQTT subscriber for the AiAction MQTT namespace.
    """

    def __init__(self):
        """
        Initialize the MQTT client.
        """

        self.host = settings.MQTT_HOST
        self.port = settings.MQTT_PORT

        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD

        self.topic = "aiaction/#"

        # --------------------------------------------------------------
        # Create MQTT client
        # --------------------------------------------------------------

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="monitoring-app-subscriber",
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
        # TLS
        # --------------------------------------------------------------

        if settings.MQTT_TLS:
            self.client.tls_set()

        # --------------------------------------------------------------
        # Callbacks
        # --------------------------------------------------------------

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    # ==================================================================
    # CONNECT
    # ==================================================================

    def on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ):
        """
        Called when the MQTT client connects to EMQX Cloud.
        """

        logger.info(
            "MQTT connection result: %s",
            reason_code,
        )

        if reason_code != 0:
            logger.error(
                "Failed to connect to EMQX Cloud. "
                "Reason: %s",
                reason_code,
            )
            return

        logger.info(
            "Connected to EMQX Cloud: %s:%s",
            self.host,
            self.port,
        )

        # --------------------------------------------------------------
        # Subscribe
        # --------------------------------------------------------------

        result, message_id = client.subscribe(
            self.topic,
            qos=1,
        )

        if result == mqtt.MQTT_ERR_SUCCESS:

            logger.info(
                "Subscribed successfully to: %s",
                self.topic,
            )

        else:

            logger.error(
                "Failed to subscribe to %s. Error: %s",
                self.topic,
                result,
            )

    # ==================================================================
    # MESSAGE
    # ==================================================================

    def on_message(
        self,
        client,
        userdata,
        message,
    ):
        """
        Called whenever an MQTT message is received.

        The subscriber does not interpret the MQTT message.

        It simply passes the raw topic and payload to the service layer.
        """

        logger.info(
            "MQTT message received."
        )

        logger.info(
            "Topic: %s",
            message.topic,
        )

        try:

            process_mqtt_message(
                topic=message.topic,
                payload=message.payload,
            )

        except Exception:

            # --------------------------------------------------------------
            # An error processing one message must never kill the
            # long-running MQTT subscriber.
            # --------------------------------------------------------------

            logger.exception(
                "Error processing MQTT message: %s",
                message.topic,
            )
        
    # ==================================================================
    # DISCONNECT
    # ==================================================================

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
            "Disconnected from EMQX Cloud. Reason: %s",
            reason_code,
        )

    # ==================================================================
    # START
    # ==================================================================

    def start(self):
        """
        Connect to EMQX Cloud and keep the subscriber running.
        """

        logger.info(
            "Starting MQTT subscriber..."
        )

        logger.info(
            "Connecting to EMQX Cloud %s:%s",
            self.host,
            self.port,
        )

        self.client.connect(
            self.host,
            self.port,
            keepalive=60,
        )

        self.client.loop_forever()

    # ==================================================================
    # STOP
    # ==================================================================

    def stop(self):
        """
        Disconnect the MQTT client cleanly.
        """

        logger.info(
            "Stopping MQTT subscriber..."
        )

        self.client.disconnect()
# connects to the broker, receives the messages and runs the periodic reconciliation

import logging
import threading

import paho.mqtt.client as mqtt
from django.conf import settings

from monitoring.services.mqtt_reconciliation import (
    finish_reconcile_window,
    start_reconcile_window,
)
from mqtt.service import process_mqtt_message

logger = logging.getLogger(__name__)


# mqtt client that listens to aiaction/# and hands every message to the service
class MQTTSubscriber:
    # reads the settings and sets up the client, its callbacks and the reconcile timers
    def __init__(self):
        self.host = settings.MQTT_HOST
        self.port = settings.MQTT_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD
        self.keepalive = settings.MQTT_KEEPALIVE
        self.topic = "aiaction/#"

        # interval: how often the subscription is renewed so the broker resends retained messages
        # window: how long to wait for those messages before marking devices and cameras as missing
        self.reconcile_interval_seconds = max(
            60, settings.MQTT_RECONCILE_INTERVAL_MINUTES * 60
        )
        self.reconcile_window_seconds = max(1, settings.MQTT_RECONCILE_WINDOW_SECONDS)

        self._reconcile_timer = None
        self._reconcile_scheduler_thread = None
        self._stop_event = threading.Event()

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="monitoring-app-subscriber",
        )

        if self.username:
            self.client.username_pw_set(username=self.username, password=self.password)

        if settings.MQTT_TLS:
            self.client.tls_set()

        # the network loop runs in its own thread, so let it reconnect by itself
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    # subscribes to the topic once the broker connection is made
    def on_connect(self, client, userdata, flags, reason_code, properties):
        logger.info("MQTT connection result: %s", reason_code)

        if reason_code != 0:
            logger.error("Failed to connect to EMQX Cloud. Reason: %s", reason_code)
            return

        logger.info("Connected to EMQX Cloud: %s:%s", self.host, self.port)

        # also reconcile on every connect, a new subscription already makes the broker resend messages
        self._subscribe_and_reconcile(client)

    # subscribes again and opens a reconciliation window
    def _subscribe_and_reconcile(self, client):
        start_reconcile_window()

        result, _message_id = client.subscribe(self.topic, qos=1)

        if result == mqtt.MQTT_ERR_SUCCESS:
            logger.info("Subscribed successfully to: %s", self.topic)
        else:
            logger.error("Failed to subscribe to %s. Error: %s", self.topic, result)

        self._schedule_reconcile_finish()

    # schedules the end of the current reconciliation window
    def _schedule_reconcile_finish(self):
        if self._reconcile_timer is not None:
            self._reconcile_timer.cancel()

        self._reconcile_timer = threading.Timer(
            self.reconcile_window_seconds, self._finish_reconcile
        )
        self._reconcile_timer.daemon = True
        self._reconcile_timer.start()

    # closes the reconciliation window and logs what was not seen
    def _finish_reconcile(self):
        try:
            result = finish_reconcile_window()
            logger.info(
                "MQTT reconciliation: %s device(s), %s camera(s) not on MQTT.",
                result["missing_devices"],
                result["missing_cameras"],
            )
        except Exception:
            logger.exception("Error finishing MQTT reconciliation window.")

    # renews the subscription every reconcile interval so the broker resends its messages
    def _reconcile_loop(self):
        while not self._stop_event.wait(self.reconcile_interval_seconds):
            try:
                if not self.client.is_connected():
                    continue

                logger.info("Starting periodic MQTT reconciliation cycle...")
                self.client.unsubscribe(self.topic)
                self._subscribe_and_reconcile(self.client)
            except Exception:
                logger.exception("Error running periodic MQTT reconciliation cycle.")

    # passes a raw message to the service, a bad message never stops the subscriber
    def on_message(self, client, userdata, message):
        logger.info("MQTT message received. Topic: %s", message.topic)

        try:
            process_mqtt_message(topic=message.topic, payload=message.payload)
        except Exception:
            logger.exception("Error processing MQTT message: %s", message.topic)

    # logs when the broker connection is lost
    def on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties
    ):
        logger.warning("Disconnected from EMQX Cloud. Reason: %s", reason_code)

    # connects to the broker and blocks until stop is called
    def start(self):
        logger.info("Starting MQTT subscriber...")
        logger.info("Connecting to EMQX Cloud %s:%s", self.host, self.port)

        self.client.connect(self.host, self.port, keepalive=self.keepalive)
        self.client.loop_start()

        self._reconcile_scheduler_thread = threading.Thread(
            target=self._reconcile_loop, daemon=True
        )
        self._reconcile_scheduler_thread.start()

        # the network loop runs in the background, wait here until stop is called
        self._stop_event.wait()

    # stops the timers and disconnects from the broker
    def stop(self):
        logger.info("Stopping MQTT subscriber...")
        self._stop_event.set()

        if self._reconcile_timer is not None:
            self._reconcile_timer.cancel()

        self.client.loop_stop()
        self.client.disconnect()

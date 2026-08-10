from devices.models import Device, DeviceStatus, DeviceType
from countries.models import Country
from customers.models import Customer
from locations.models import Location
from django.test import TestCase
from monitoring.models import DeviceAlert, AlertType

from mqtt.service import process_mqtt_message



class MQTTServiceTests(TestCase):
    """
    Tests the MQTT parser → service → monitoring pipeline.

    No MQTT broker is required.

    We simulate the exact MQTT topics and payloads that EMQX would
    deliver to the application.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create the Device hierarchy used by the tests.
        """

        cls.country = Country.objects.create(
            name="Portugal",
            code="PT",
        )

        cls.customer = Customer.objects.create(
            country=cls.country,
            name="aitecserv",
        )

        cls.location = Location.objects.create(
            customer=cls.customer,
            name="office2",
        )

        cls.device = Device.objects.create(
            location=cls.location,
            name="Edge 01",
            mqtt_identifier="edge-01",
            serial_number="EDGE-001",
            device_type=DeviceType.EDGE,
            status=DeviceStatus.UNKNOWN,
        )

    # ========================================================================
    # Status message
    # ========================================================================

    def test_online_status_message_updates_device(self):
        """
        Simulate:

        aiaction/pt/aitecserv/office2/edge-01/status/aiaction-edge
        """

        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "status/"
            "aiaction-edge"
        )

        payload = {
            "status": "online",
            "version": "1.0.0",
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
        }

        process_mqtt_message(
            topic=topic,
            payload=payload,
        )

        self.device.refresh_from_db()

        self.assertEqual(
            self.device.status,
            DeviceStatus.ONLINE,
        )

        self.assertIsNotNone(
            self.device.last_seen,
        )

    # ========================================================================
    # Health message
    # ========================================================================

    def test_health_message_updates_device(self):
        """
        Simulate:

        aiaction/pt/aitecserv/office2/edge-01/health
        """

        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health"
        )

        payload = {
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
            "ttl_seconds": 60,
            "components": {
                "aiaction_edge": {
                    "status": "up",
                },
                "detector": {
                    "status": "up",
                    "latency_ms": 42,
                },
                "idmr": {
                    "status": "up",
                    "latency_ms": 31,
                },
                "requests": {
                    "status": "up",
                },
            },
        }

        process_mqtt_message(
            topic=topic,
            payload=payload,
        )

        self.device.refresh_from_db()

        self.assertEqual(
            self.device.status,
            DeviceStatus.ONLINE,
        )

        self.assertIsNotNone(
            self.device.last_seen,
        )

    # ========================================================================
    # Unhealthy component
    # ========================================================================

    def test_health_message_creates_alert_for_unhealthy_component(self):
        """
        A component going DOWN should create a health alert.

        The device itself remains ONLINE.
        """

        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health"
        )

        payload = {
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
            "ttl_seconds": 60,
            "components": {
                "aiaction_edge": {
                    "status": "up",
                },
                "detector": {
                    "status": "down",
                },
                "idmr": {
                    "status": "up",
                },
                "requests": {
                    "status": "up",
                },
            },
        }

        process_mqtt_message(
            topic=topic,
            payload=payload,
        )

        self.device.refresh_from_db()

        # The device is still communicating.
        self.assertEqual(
            self.device.status,
            DeviceStatus.ONLINE,
        )

        # A health alert should exist.
        self.assertTrue(
            DeviceAlert.objects.filter(
                device=self.device,
                alert_type=AlertType.DEVICE_HEALTH,
                active=True,
            ).exists()
        )

    # ========================================================================
    # Camera-level message
    # ========================================================================

    def test_camera_alert_topic_is_parsed_without_changing_device_status(self):
        """
        Camera-level messages are currently parsed and routed through
        the MQTT service, but they are not persisted yet.

        Example:

        aiaction/pt/aitecserv/office2/edge-01/
        AXIS-B8A44F957EC7/ch1/alert
        """

        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "AXIS-B8A44F957EC7/"
            "ch1/"
            "alert"
        )

        payload = {
            "action_code": "HighProbFireDetected",
            "class_label": "smoke",
            "confidence": 0.8741,
            "bounding_box": [
                1251,
                798,
                1412,
                971,
            ],
            "case": "Inside Normal zone",
            "is_first_trigger": True,
            "trigger_count": 1,
            "timestamp": "2026-07-15T14:35:00Z",
            "source": "aiaction",
        }

        result = process_mqtt_message(
            topic=topic,
            payload=payload,
        )

        self.assertEqual(
            result,
            self.device,
        )


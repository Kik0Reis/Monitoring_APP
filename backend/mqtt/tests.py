from django.test import TestCase

from cameras.models import Camera, CameraStatus
from countries.models import Country
from customers.models import Customer
from devices.models import Device, DeviceStatus, DeviceType
from locations.models import Location
from monitoring.models import AlertType, CameraAlert, CameraAlertType, DeviceAlert
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

    # Status message

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

    # Health message

    def test_health_message_updates_device(self):
        """
        Simulate:

        aiaction/pt/aitecserv/office2/edge-01/health
        """

        topic = "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "health"

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

    # Unhealthy component

    def test_health_message_creates_alert_for_unhealthy_component(self):
        """
        A component going DOWN should create a health alert.

        The device itself remains ONLINE.
        """

        topic = "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "health"

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

    # Camera-level message

    def test_camera_alert_for_unknown_camera_is_ignored(self):
        """
        Unlike the ".../cameras" bulk status list, a single-camera alert
        does NOT auto-create the camera if it doesn't exist yet — an
        "alert" is a real-world detection, and we don't want to invent a
        Camera record from one just to hang it off. The message should be
        dropped (with a warning logged) and the Edge device left alone.

        Example topic:

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

        self.assertIsNone(result)

        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.UNKNOWN)

    def test_camera_alert_for_known_camera_creates_alert(self):
        """
        Same topic as above, but this time the camera already exists —
        the alert should be recorded and the camera marked ONLINE (it
        clearly is, since it just sent us a detection).
        """

        camera = Camera.objects.create(
            device=self.device,
            camera_identifier="AXIS-B8A44F957EC7",
            channel=1,
            name="Front door",
            status=CameraStatus.UNKNOWN,
        )

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
            "timestamp": "2026-07-15T14:35:00Z",
            "source": "aiaction",
        }

        result = process_mqtt_message(topic=topic, payload=payload)

        self.assertEqual(result, camera)

        camera.refresh_from_db()
        self.assertEqual(camera.status, CameraStatus.ONLINE)

        self.assertTrue(
            CameraAlert.objects.filter(
                camera=camera,
                alert_type=CameraAlertType.CAMERA_ALERT,
                active=True,
            ).exists()
        )

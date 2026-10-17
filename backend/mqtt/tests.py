# tests for the mqtt messages that update devices, cameras and alerts

from django.test import TestCase

from cameras.models import Camera, CameraStatus
from countries.models import Country
from customers.models import Customer
from devices.models import Device, DeviceStatus, DeviceType
from locations.models import Location
from monitoring.models import AlertType, CameraAlert, CameraAlertType, DeviceAlert
from mqtt.service import process_mqtt_message


# tests for the mqtt pipeline: parser, service and monitoring
class MQTTServiceTests(TestCase):
    # creates the records used by the tests
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.create(name="Portugal", code="PT")

        cls.customer = Customer.objects.create(country=cls.country, name="aitecserv")

        cls.location = Location.objects.create(customer=cls.customer, name="office2")

        cls.device = Device.objects.create(
            location=cls.location,
            name="Edge 01",
            mqtt_identifier="edge-01",
            serial_number="EDGE-001",
            device_type=DeviceType.EDGE,
            status=DeviceStatus.UNKNOWN,
        )


    # online status message updates device
    def test_online_status_message_updates_device(self):
        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health/"
            "edge-device"
        )

        payload = {
            "status": "online",
            "version": "1.0.0",
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
        }

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

        self.assertIsNotNone(self.device.last_seen)

    # offline status message updates device
    def test_offline_status_message_updates_device(self):
        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health/"
            "edge-device"
        )

        payload = {
            "status": "offline",
            "reason": "lwt",
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "mqtt-broker",
        }

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        self.assertEqual(self.device.status, DeviceStatus.OFFLINE)

        self.assertTrue(
            DeviceAlert.objects.filter(
                device=self.device, alert_type=AlertType.DEVICE_OFFLINE, active=True
            ).exists()
        )


    # overall health message updates device
    def test_overall_health_message_updates_device(self):
        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health/"
            "overall-health"
        )

        payload = {
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
            "ttl_seconds": 60,
            "components": {
                "edge-device": {"status": "online", "version": "1.0.0"},
                "cameras": {
                    "cameras": [
                        {
                            "camera_id": "CAM-1",
                            "status": "online",
                            "seconds_since_last_seen": 7.5,
                        }
                    ]
                },
                "detectorapi": {"status": "up"},
                "detector": {"status": "up", "latency_ms": 42},
                "idmr": {"status": "up", "latency_ms": 31},
            },
        }

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

        self.assertIsNotNone(self.device.last_seen)

        # the nested camera list should have been provisioned/updated too
        camera = Camera.objects.get(device=self.device, camera_identifier="CAM-1")

        self.assertEqual(camera.status, CameraStatus.ONLINE)


    # overall health message creates alert for unhealthy component
    def test_overall_health_message_creates_alert_for_unhealthy_component(self):
        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health/"
            "overall-health"
        )

        payload = {
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
            "ttl_seconds": 60,
            "components": {
                "edge-device": {"status": "online"},
                "detectorapi": {"status": "up"},
                "detector": {"status": "down"},
                "idmr": {"status": "up"},
            },
        }

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        # the device is still communicating
        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

        # A health alert should exist
        self.assertTrue(
            DeviceAlert.objects.filter(
                device=self.device, alert_type=AlertType.DEVICE_HEALTH, active=True
            ).exists()
        )


    # component health message updates device
    def test_component_health_message_updates_device(self):
        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health/"
            "detectorapi"
        )

        payload = {
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
            "status": "up",
            "initialized": True,
            "configs_loaded": True,
            "active_camera_count": 0,
        }

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        self.assertEqual(self.device.status, DeviceStatus.ONLINE)
        self.assertEqual(self.device.component_statuses["detectorapi"]["status"], "up")


    # health cameras message updates cameras
    def test_health_cameras_message_updates_cameras(self):
        topic = (
            "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "health/" "cameras"
        )

        payload = {
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
            "cameras": [
                {
                    "camera_id": "AXIS-B8A44F957EC7",
                    "status": "offline",
                    "seconds_since_last_seen": 18426.2,
                }
            ],
        }

        process_mqtt_message(topic=topic, payload=payload)

        camera = Camera.objects.get(
            device=self.device, camera_identifier="AXIS-B8A44F957EC7"
        )

        self.assertEqual(camera.status, CameraStatus.OFFLINE)


    # device info message stores system info
    def test_device_info_message_stores_system_info(self):
        topic = (
            "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "info/" "edge-device"
        )

        payload = {
            "timestamp": "2026-07-15T14:30:00Z",
            "device_id": "DESKTOP-6F7A8IL-4c38d521021e",
            "device_name": "DESKTOP-6F7A8IL",
            "device_os": "Windows 10",
            "cpu_physical_cores": 6,
            "ram_total_gb": 63.82,
            "ip_address": "192.168.10.110",
        }

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        self.assertEqual(self.device.system_info["device_os"], "Windows 10")

    # device info replaces placeholder serial number
    def test_device_info_replaces_placeholder_serial_number(self):
        self.device.pending_review = True
        self.device.save(update_fields=["pending_review"])

        topic = (
            "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "info/" "edge-device"
        )

        payload = {"device_id": "DESKTOP-6F7A8IL-4c38d521021e", "device_os": "Windows 10"}

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        self.assertEqual(self.device.serial_number, "DESKTOP-6F7A8IL-4c38d521021e")

    # device info does not replace confirmed serial number
    def test_device_info_does_not_replace_confirmed_serial_number(self):
        self.device.pending_review = False
        self.device.save(update_fields=["pending_review"])

        topic = (
            "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "info/" "edge-device"
        )

        payload = {"device_id": "DESKTOP-6F7A8IL-4c38d521021e"}

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        self.assertEqual(self.device.serial_number, "EDGE-001")

    # overall health does not store edge device as a component
    def test_overall_health_does_not_store_edge_device_as_a_component(self):
        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health/"
            "overall-health"
        )

        payload = {
            "components": {
                "edge-device": {"status": "online", "version": "1.0.0"},
                "detectorapi": {"status": "up"},
            }
        }

        process_mqtt_message(topic=topic, payload=payload)

        self.device.refresh_from_db()

        self.assertNotIn("edge-device", self.device.component_statuses)
        self.assertIn("detectorapi", self.device.component_statuses)

    # component health extracts per camera breakdown
    def test_component_health_extracts_per_camera_breakdown(self):
        camera = Camera.objects.create(
            device=self.device, camera_identifier="AXIS-B8A44F957EC7", channel=1
        )

        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "health/"
            "detectorapi"
        )

        payload = {
            "status": "up",
            "cameras": {
                "AXIS-B8A44F957EC7_ch1": {
                    "stage": "idle",
                    "request_id": "abc123",
                    "error": None,
                }
            },
        }

        process_mqtt_message(topic=topic, payload=payload)

        camera.refresh_from_db()

        self.assertEqual(camera.health_data["detectorapi"]["stage"], "idle")


    # camera info message provisions camera identity
    def test_camera_info_message_provisions_camera_identity(self):
        topic = "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "info/" "cameras"

        payload = {
            "timestamp": "2026-07-15T10:13:49Z",
            "source": "aiaction",
            "cameras": [
                {
                    "camera_id": "CAM-1",
                    "camera_serial_number": "B8A44F957EC7",
                    "name": "Test Camera",
                    "latitude": None,
                    "longitude": None,
                }
            ],
        }

        process_mqtt_message(topic=topic, payload=payload)

        camera = Camera.objects.get(device=self.device, camera_identifier="CAM-1")

        self.assertTrue(camera.pending_review)
        self.assertEqual(camera.serial_number, "B8A44F957EC7")
        self.assertEqual(camera.name, "Test Camera")

    # camera info message does not overwrite confirmed camera
    def test_camera_info_message_does_not_overwrite_confirmed_camera(self):
        camera = Camera.objects.create(
            device=self.device,
            camera_identifier="CAM-1",
            channel=1,
            name="Front Door Camera",
            pending_review=False,
        )

        topic = "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "info/" "cameras"

        payload = {
            "cameras": [
                {
                    "camera_id": "CAM-1",
                    "camera_serial_number": "B8A44F957EC7",
                    "name": "Test Camera",
                }
            ]
        }

        process_mqtt_message(topic=topic, payload=payload)

        camera.refresh_from_db()

        self.assertEqual(camera.name, "Front Door Camera")


    # license message stores license data on matching camera
    def test_license_message_stores_license_data_on_matching_camera(self):
        camera = Camera.objects.create(
            device=self.device,
            camera_identifier="AXIS-B8A44F957EC7",
            channel=1,
            name="Fire Camera",
        )

        topic = "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "info/" "licenses"

        payload = {
            "timestamp": "2026-09-16T07:26:19+01:00",
            "source": "aiaction",
            "licenses": [
                {
                    "camera_id": "AXIS-B8A44F957EC7",
                    "camera_name": "Fire Camera",
                    "channel_number": 1,
                    "licensed": True,
                    "status": True,
                    "begin_date": "2026-09-16",
                    "end_date": "2027-09-17",
                    "days_left": 366,
                    "last_validation_ok": True,
                    "last_validation_error": None,
                    "last_validation_at": "2026-09-16T11:56:19.762664",
                },
                {
                    "camera_id": "Test-1",
                    "camera_name": "Test Camera",
                    "channel_number": 1,
                    "licensed": False,
                    "status": None,
                    "begin_date": None,
                    "end_date": None,
                    "days_left": None,
                    "last_validation_ok": None,
                    "last_validation_error": None,
                    "last_validation_at": None,
                },
            ],
        }

        process_mqtt_message(topic=topic, payload=payload)

        camera.refresh_from_db()

        self.assertTrue(camera.license_data["licensed"])
        self.assertEqual(camera.license_data["days_left"], 366)

    # license message skips unknown camera
    def test_license_message_skips_unknown_camera(self):
        topic = "aiaction/" "pt/" "aitecserv/" "office2/" "edge-01/" "info/" "licenses"

        payload = {
            "licenses": [
                {
                    "camera_id": "Test-1",
                    "channel_number": 1,
                    "licensed": False,
                    "status": None,
                }
            ]
        }

        process_mqtt_message(topic=topic, payload=payload)

        self.assertFalse(
            Camera.objects.filter(device=self.device, camera_identifier="Test-1").exists()
        )


    # issue message creates device error alert
    def test_issue_message_creates_device_error_alert(self):
        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "issues/"
            "disk-space-low"
        )

        payload = {"message": "Disk usage above 90%.", "severity": "warning"}

        process_mqtt_message(topic=topic, payload=payload)

        self.assertTrue(
            DeviceAlert.objects.filter(
                device=self.device, alert_type=AlertType.DEVICE_ERROR, active=True
            ).exists()
        )


    # detection for unknown camera is ignored
    def test_detection_for_unknown_camera_is_ignored(self):
        topic = (
            "aiaction/"
            "pt/"
            "aitecserv/"
            "office2/"
            "edge-01/"
            "detections/"
            "AXIS-B8A44F957EC7/"
            "1"
        )

        payload = {
            "action_code": "HighProbFireDetected",
            "class_label": "smoke",
            "confidence": 0.8741,
            "bounding_box": [1251, 798, 1412, 971],
            "case": "Inside Normal zone",
            "is_first_trigger": True,
            "trigger_count": 1,
            "timestamp": "2026-07-15T14:35:00Z",
            "source": "aiaction",
        }

        result = process_mqtt_message(topic=topic, payload=payload)

        self.assertIsNone(result)

        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.UNKNOWN)

    # detection for known camera creates alert
    def test_detection_for_known_camera_creates_alert(self):
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
            "detections/"
            "AXIS-B8A44F957EC7/"
            "1"
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
                camera=camera, alert_type=CameraAlertType.CAMERA_ALERT, active=True
            ).exists()
        )

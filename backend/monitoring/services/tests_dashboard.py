"""
Tests for the newer parts of monitoring/services/dashboard.py:

- Camera-offline alerts showing up in the "problems" list.
- Locations reporting *what* is wrong, not just a count.
- Detections being included in the main dashboard payload.
"""

from django.test import TestCase

from cameras.models import Camera, CameraStatus
from countries.models import Country
from customers.models import Customer
from devices.models import Device, DeviceStatus, DeviceType
from locations.models import Location
from monitoring.services.camera_monitor import (
    create_camera_offline_alert,
    process_camera_detection,
)
from monitoring.services.dashboard import (
    get_camera_detections,
    get_dashboard_data,
    get_locations_with_problems,
    get_problem_alerts,
)


class DashboardProblemsAndDetectionsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        country = Country.objects.create(name="Portugal", code="PT")
        customer = Customer.objects.create(country=country, name="aitecserv")
        cls.location = Location.objects.create(customer=customer, name="office2")

        cls.device = Device.objects.create(
            location=cls.location,
            name="Edge 01",
            mqtt_identifier="edge-01",
            serial_number="EDGE-001",
            device_type=DeviceType.EDGE,
            status=DeviceStatus.ONLINE,
        )

        cls.camera = Camera.objects.create(
            device=cls.device,
            name="Front door",
            camera_identifier="AXIS-1",
            channel=1,
            status=CameraStatus.OFFLINE,
        )

    def test_camera_offline_alert_appears_in_problem_alerts(self):
        create_camera_offline_alert(self.camera)

        problems = get_problem_alerts(limit=10, active_only=True)

        camera_problems = [p for p in problems if p["camera_id"] == self.camera.id]
        self.assertEqual(len(camera_problems), 1)
        self.assertEqual(camera_problems[0]["alert_type"], "CAMERA_OFFLINE")

    def test_location_with_offline_camera_lists_the_issue_in_plain_english(self):
        create_camera_offline_alert(self.camera)

        locations = get_locations_with_problems()

        matching = [loc for loc in locations if loc["id"] == self.location.id]
        self.assertEqual(len(matching), 1)

        location = matching[0]
        self.assertIn("1 camera(s) offline", location["issues"])

    def test_dashboard_data_includes_recent_detections(self):
        process_camera_detection(
            camera=self.camera,
            payload={
                "action_code": "HighProbFireDetected",
                "class_label": "smoke",
                "confidence": 0.91,
            },
        )

        data = get_dashboard_data()

        self.assertIn("recent_detections", data)
        self.assertEqual(len(data["recent_detections"]), 1)
        self.assertEqual(data["recent_detections"][0]["camera_id"], self.camera.id)

        # Sanity-check the lower-level function too, since the dashboard
        # payload just wraps it.
        detections = get_camera_detections(limit=10)
        self.assertEqual(len(detections), 1)

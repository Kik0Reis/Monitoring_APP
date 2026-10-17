from django.test import TestCase

from cameras.models import Camera, CameraStatus
from countries.models import Country
from customers.models import Customer
from devices.models import Device, DeviceStatus, DeviceType
from locations.models import Location
from monitoring.services.alert_lists import get_camera_detections, get_problem_alerts
from monitoring.services.camera_monitor import (
    create_camera_offline_alert,
    process_camera_detection,
)
from monitoring.services.dashboard import (
    get_dashboard_data,
    get_dashboard_summary,
    get_devices_with_problems,
    get_locations_with_problems,
)
from monitoring.services.device_health import create_offline_alert
from monitoring.services.tree import get_monitor_tree

DETECTION_PAYLOAD = {
    "action_code": "HighProbFireDetected",
    "class_label": "smoke",
    "confidence": 0.91,
}


# tests for the problem lists, the locations list and the detections in the dashboard payload
class DashboardProblemsAndDetectionsTests(TestCase):
    # creates the records used by the tests
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

    # a camera offline alert is listed with the other problems
    def test_camera_offline_alert_appears_in_problem_alerts(self):
        create_camera_offline_alert(self.camera)

        problems = get_problem_alerts(limit=10)

        camera_problems = [p for p in problems if p["camera_id"] == self.camera.id]
        self.assertEqual(len(camera_problems), 1)
        self.assertEqual(camera_problems[0]["alert_type"], "CAMERA_OFFLINE")

    # a location with an offline camera says so in plain english
    def test_location_with_offline_camera_lists_the_issue_in_plain_english(self):
        create_camera_offline_alert(self.camera)

        matching = [loc for loc in get_locations_with_problems() if loc["id"] == self.location.id]

        self.assertEqual(len(matching), 1)
        self.assertIn("1 camera(s) offline", matching[0]["issues"])

    # the dashboard payload includes the recent detections
    def test_dashboard_data_includes_recent_detections(self):
        process_camera_detection(camera=self.camera, payload=DETECTION_PAYLOAD)

        data = get_dashboard_data()

        self.assertEqual(len(data["recent_detections"]), 1)
        self.assertEqual(data["recent_detections"][0]["camera_id"], self.camera.id)
        self.assertEqual(len(get_camera_detections(limit=10)), 1)


# tests that hide_inactive removes inactive devices and cameras from every dashboard list
class DashboardHideInactiveTests(TestCase):
    # creates one active and one inactive device, each with a camera
    @classmethod
    def setUpTestData(cls):
        country = Country.objects.create(name="Portugal", code="PT")
        customer = Customer.objects.create(country=country, name="aitecserv")
        cls.location = Location.objects.create(customer=customer, name="office")

        cls.active_device = cls._make_device("Active Edge", "edge-a", "EDGE-A", active=True)
        cls.inactive_device = cls._make_device("Inactive Edge", "edge-i", "EDGE-I", active=False)

        cls.active_camera = Camera.objects.create(
            device=cls.active_device, name="Active cam", camera_identifier="CAM-A", channel=1,
            status=CameraStatus.OFFLINE,
        )
        cls.inactive_camera = Camera.objects.create(
            device=cls.active_device, name="Inactive cam", camera_identifier="CAM-I", channel=2,
            status=CameraStatus.OFFLINE, active=False,
        )

    # creates an offline edge device in the test location
    @classmethod
    def _make_device(cls, name, identifier, serial, active):
        return Device.objects.create(
            location=cls.location,
            name=name,
            mqtt_identifier=identifier,
            serial_number=serial,
            device_type=DeviceType.EDGE,
            status=DeviceStatus.OFFLINE,
            active=active,
        )

    # offline alerts of inactive devices and cameras are hidden only when asked
    def test_offline_alerts_of_inactive_records_are_hidden(self):
        create_offline_alert(self.active_device)
        create_offline_alert(self.inactive_device)
        create_camera_offline_alert(self.active_camera)
        create_camera_offline_alert(self.inactive_camera)

        names = lambda alerts: {a["camera_name"] or a["device_name"] for a in alerts}

        self.assertEqual(
            names(get_problem_alerts(limit=50, category="offline", hide_inactive=True)),
            {"Active Edge", "Active cam"},
        )
        self.assertEqual(
            names(get_problem_alerts(limit=50, category="offline")),
            {"Active Edge", "Inactive Edge", "Active cam", "Inactive cam"},
        )

    # the summary counts only active devices and cameras when hiding inactive ones
    def test_summary_counts_follow_the_scope(self):
        hidden = get_dashboard_summary(hide_inactive=True)
        shown = get_dashboard_summary()

        self.assertEqual((hidden["devices"], hidden["cameras"]), (1, 1))
        self.assertEqual((shown["devices"], shown["cameras"]), (2, 2))

    # the devices list leaves out inactive devices when hiding them
    def test_devices_with_problems_follow_the_scope(self):
        hidden = {d["name"] for d in get_devices_with_problems(hide_inactive=True)}
        shown = {d["name"] for d in get_devices_with_problems()}

        self.assertEqual(hidden, {"Active Edge"})
        self.assertEqual(shown, {"Active Edge", "Inactive Edge"})

    # a location only counts its active devices and cameras when hiding inactive ones
    def test_location_counts_follow_the_scope(self):
        hidden = get_locations_with_problems(hide_inactive=True)[0]
        shown = get_locations_with_problems()[0]

        self.assertEqual((hidden["offline_devices"], hidden["offline_cameras"]), (1, 1))
        self.assertEqual((shown["offline_devices"], shown["offline_cameras"]), (2, 2))

    # a location that is itself inactive disappears, together with its devices
    def test_inactive_location_is_hidden(self):
        self.location.active = False
        self.location.save()

        self.assertEqual(get_locations_with_problems(hide_inactive=True), [])
        self.assertEqual(get_devices_with_problems(hide_inactive=True), [])
        self.assertEqual(get_dashboard_summary(hide_inactive=True)["devices"], 0)

    # detections from inactive cameras are hidden only when asked
    def test_detections_follow_the_scope(self):
        process_camera_detection(camera=self.active_camera, payload=DETECTION_PAYLOAD)
        process_camera_detection(camera=self.inactive_camera, payload=DETECTION_PAYLOAD)

        self.assertEqual(len(get_camera_detections(hide_inactive=True)), 1)
        self.assertEqual(len(get_camera_detections()), 2)

    # an offline inactive camera turns the tree red only when inactive records are shown
    def test_tree_rollup_follows_the_scope(self):
        self.active_camera.status = CameraStatus.ONLINE
        self.active_camera.save()
        self.active_device.status = DeviceStatus.ONLINE
        self.active_device.save()
        self.inactive_device.delete()

        # returns the color of the first device node of the tree
        def device_color(hide_inactive):
            tree = get_monitor_tree(hide_inactive=hide_inactive)
            return tree[0]["children"][0]["children"][0]["children"][0]["system_check"]

        self.assertEqual(device_color(hide_inactive=True), "green")
        self.assertEqual(device_color(hide_inactive=False), "red")

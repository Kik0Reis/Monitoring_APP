"""
Tests for the device health monitoring service.

These tests verify the business rules for MQTT health messages.

They do NOT require:
- EMQX
- an MQTT broker
- a network connection

They use Django's test database to verify that the monitoring service
correctly updates Device, DeviceHeartbeat, and DeviceAlert records.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from cameras.models import Camera, CameraStatus
from countries.models import Country
from customers.models import Customer
from devices.models import Device, DeviceStatus, DeviceType
from locations.models import Location
from monitoring.models import (
    AlertSeverity,
    AlertType,
    CameraAlert,
    CameraAlertType,
    DeviceAlert,
    DeviceHeartbeat,
)
from monitoring.services.device_health import process_overall_health
from monitoring.services.heartbeat_monitor import (
    check_all_heartbeats,
    check_camera_timeout,
    check_device_timeout,
)


class CameraHeartbeatTimeoutTests(TestCase):
    """
    Tests for camera heartbeat timeout/offline detection.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create the hierarchy required by Camera.

        Country
            ↓
        Customer
            ↓
        Location
            ↓
        Edge Device
            ↓
        Camera
        """

        cls.country = Country.objects.create(name="Portugal", code="PT")

        cls.customer = Customer.objects.create(country=cls.country, name="aitecserv")

        cls.location = Location.objects.create(customer=cls.customer, name="office2")

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
            name="Camera 01",
            camera_identifier="AXIS-B8A44F957EC7",
            channel=1,
            status=CameraStatus.ONLINE,
        )

    # Camera is still healthy

    def test_camera_remains_online_within_timeout(self):
        """
        A camera remains ONLINE when its last communication is still
        inside the allowed timeout window.
        """

        now = timezone.now()

        self.camera.last_seen = now - timedelta(seconds=30)

        self.camera.save(update_fields=["last_seen"])

        check_camera_timeout(camera=self.camera, timeout_seconds=60, now=now)

        self.camera.refresh_from_db()

        self.assertEqual(self.camera.status, CameraStatus.ONLINE)

    # Camera becomes offline

    def test_camera_becomes_offline_after_timeout(self):
        """
        A camera becomes OFFLINE when its heartbeat has expired, and a
        CAMERA_OFFLINE alert is raised so it shows up on the dashboard.
        """

        now = timezone.now()

        self.camera.last_seen = now - timedelta(seconds=61)

        self.camera.save(update_fields=["last_seen"])

        check_camera_timeout(camera=self.camera, timeout_seconds=60, now=now)

        self.camera.refresh_from_db()

        self.assertEqual(self.camera.status, CameraStatus.OFFLINE)

        self.assertTrue(
            CameraAlert.objects.filter(
                camera=self.camera,
                alert_type=CameraAlertType.CAMERA_OFFLINE,
                active=True,
            ).exists()
        )

    def test_camera_offline_alert_resolves_when_camera_comes_back(self):
        """
        Once a camera reports in again (any status update to ONLINE), the
        CAMERA_OFFLINE alert raised while it was down should auto-resolve
        — mirroring how DEVICE_OFFLINE already works for Edge devices.
        """

        now = timezone.now()

        self.camera.last_seen = now - timedelta(seconds=61)
        self.camera.save(update_fields=["last_seen"])

        check_camera_timeout(camera=self.camera, timeout_seconds=60, now=now)

        from monitoring.services.camera_monitor import update_camera_status

        update_camera_status(camera=self.camera, new_status=CameraStatus.ONLINE)

        self.assertFalse(
            CameraAlert.objects.filter(
                camera=self.camera,
                alert_type=CameraAlertType.CAMERA_OFFLINE,
                active=True,
            ).exists()
        )

    # Never-seen camera

    def test_camera_without_last_seen_remains_unknown(self):
        """
        A camera that has never communicated remains UNKNOWN.
        """

        self.camera.status = CameraStatus.UNKNOWN
        self.camera.last_seen = None

        self.camera.save(update_fields=["status", "last_seen"])

        check_camera_timeout(camera=self.camera, timeout_seconds=60)

        self.camera.refresh_from_db()

        self.assertEqual(self.camera.status, CameraStatus.UNKNOWN)

    # Camera timeout does not change Edge status

    def test_camera_timeout_does_not_change_device_status(self):
        """
        A camera becoming OFFLINE does not automatically make its
        Edge device OFFLINE.

        The Edge device has its own heartbeat.
        """

        now = timezone.now()

        self.device.status = DeviceStatus.ONLINE
        self.device.last_seen = now

        self.device.save(update_fields=["status", "last_seen"])

        self.camera.last_seen = now - timedelta(seconds=61)

        self.camera.save(update_fields=["last_seen"])

        check_camera_timeout(camera=self.camera, timeout_seconds=60, now=now)

        self.camera.refresh_from_db()
        self.device.refresh_from_db()

        self.assertEqual(self.camera.status, CameraStatus.OFFLINE)

        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

    # Combined heartbeat monitor

    def test_check_all_heartbeats_checks_devices_and_cameras(self):
        """
        The combined heartbeat monitor checks both Edge devices
        and cameras.
        """

        now = timezone.now()

        # Edge device is healthy.
        self.device.last_seen = now

        self.device.save(update_fields=["last_seen"])

        # Camera has timed out.
        self.camera.last_seen = now - timedelta(seconds=61)

        self.camera.save(update_fields=["last_seen"])

        result = check_all_heartbeats(timeout_seconds=60, now=now)

        self.device.refresh_from_db()
        self.camera.refresh_from_db()

        # Device remains online.
        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

        # Camera becomes offline.
        self.assertEqual(self.camera.status, CameraStatus.OFFLINE)

        # Combined result should report one offline camera
        # and zero offline devices.
        self.assertEqual(result["devices_offline"], 0)

        self.assertEqual(result["cameras_offline"], 1)


class DeviceHealthServiceTests(TestCase):
    """
    Tests for process_overall_health().
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create the hierarchy required by Device.

        Country
            ↓
        Customer
            ↓
        Location
            ↓
        Device
        """

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

    # Helper

    @staticmethod
    def healthy_payload():
        """
        Return a health payload where all components are healthy.
        """

        return {
            "timestamp": "2026-07-15T14:30:00Z",
            "source": "aiaction",
            "ttl_seconds": 60,
            "components": {
                "edge-device": {"status": "online"},
                "detector": {"status": "up", "latency_ms": 42},
                "idmr": {"status": "up", "latency_ms": 31},
                "requests": {"status": "up"},
            },
        }

    # Test 1

    def test_all_components_up_marks_device_online(self):
        """
        When all components report 'up':

            Device.status = ONLINE
            Device.last_seen is updated
            Heartbeat is stored
            No health alert is created
        """

        received_at = timezone.now()

        payload = self.healthy_payload()

        process_overall_health(
            device=self.device, payload=payload, received_at=received_at
        )

        # Refresh the object from the database so we verify the
        # actual persisted values.
        self.device.refresh_from_db()

        # The device is communicating, therefore it is ONLINE.
        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

        # last_seen should match the MQTT message receive time.
        self.assertEqual(self.device.last_seen, received_at)

        # One heartbeat should have been stored.
        self.assertEqual(DeviceHeartbeat.objects.filter(device=self.device).count(), 1)

        # No health alert should exist.
        self.assertFalse(
            DeviceAlert.objects.filter(
                device=self.device, alert_type=AlertType.DEVICE_HEALTH, active=True
            ).exists()
        )

    # Test 2

    def test_unhealthy_component_keeps_device_online_and_creates_alert(self):
        """
        When one internal component is down:

            Device.status = ONLINE
            Device.last_seen is updated
            Heartbeat is stored
            DEVICE_HEALTH alert is created

        The device remains ONLINE because it successfully sent
        the health message.
        """

        received_at = timezone.now()

        payload = self.healthy_payload()

        # Simulate the detector becoming unhealthy.
        payload["components"]["detector"]["status"] = "down"

        process_overall_health(
            device=self.device, payload=payload, received_at=received_at
        )

        self.device.refresh_from_db()

        # The device itself is still communicating.
        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

        # last_seen must still be updated.
        self.assertEqual(self.device.last_seen, received_at)

        # The heartbeat must be stored.
        self.assertEqual(DeviceHeartbeat.objects.filter(device=self.device).count(), 1)

        # A health alert must be created.
        alert = DeviceAlert.objects.get(
            device=self.device, alert_type=AlertType.DEVICE_HEALTH, active=True
        )

        self.assertEqual(alert.severity, AlertSeverity.WARNING)

        # The alert should identify the unhealthy component.
        self.assertIn("detector", alert.message)

        # The original MQTT payload should be preserved.
        self.assertEqual(alert.raw_payload, payload)

    # Test 3

    def test_component_recovery_resolves_health_alert(self):
        """
        When an unhealthy component recovers:

            Device.status = ONLINE
            Existing health alert becomes inactive
            resolved_at is populated
        """

        # --------------------------------------------------------------
        # First message: detector is DOWN.
        # --------------------------------------------------------------

        unhealthy_payload = self.healthy_payload()

        unhealthy_payload["components"]["detector"]["status"] = "down"

        process_overall_health(device=self.device, payload=unhealthy_payload)

        # Verify that the alert was created.
        alert = DeviceAlert.objects.get(
            device=self.device, alert_type=AlertType.DEVICE_HEALTH, active=True
        )

        self.assertTrue(alert.active)
        self.assertIsNone(alert.resolved_at)

        # --------------------------------------------------------------
        # Second message: detector has recovered.
        # --------------------------------------------------------------

        healthy_payload = self.healthy_payload()

        process_overall_health(device=self.device, payload=healthy_payload)

        self.device.refresh_from_db()

        # Device remains ONLINE.
        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

        # The previous alert should now be resolved.
        alert.refresh_from_db()

        self.assertFalse(alert.active)

        self.assertIsNotNone(alert.resolved_at)

        # There should still only be one health alert.
        #
        # We are resolving the existing alert instead of creating
        # another alert for the recovery.
        self.assertEqual(
            DeviceAlert.objects.filter(
                device=self.device, alert_type=AlertType.DEVICE_HEALTH
            ).count(),
            1,
        )


class HeartbeatTimeoutTests(TestCase):
    """
    Tests for heartbeat timeout/offline detection.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create the hierarchy required by Device.
        """

        cls.country = Country.objects.create(name="Portugal", code="PT")

        cls.customer = Customer.objects.create(country=cls.country, name="aitecserv")

        cls.location = Location.objects.create(customer=cls.customer, name="office2")

        cls.device = Device.objects.create(
            location=cls.location,
            name="Edge 01",
            mqtt_identifier="edge-01",
            serial_number="EDGE-001",
            device_type=DeviceType.EDGE,
            status=DeviceStatus.ONLINE,
        )

    # Device is still healthy

    def test_device_remains_online_within_timeout(self):
        """
        A device remains ONLINE when its last heartbeat is still
        inside the allowed timeout window.
        """

        now = timezone.now()

        self.device.last_seen = now - timedelta(seconds=30)

        self.device.save(update_fields=["last_seen"])

        check_device_timeout(device=self.device, timeout_seconds=60, now=now)

        self.device.refresh_from_db()

        self.assertEqual(self.device.status, DeviceStatus.ONLINE)

        self.assertFalse(
            DeviceAlert.objects.filter(
                device=self.device, alert_type=AlertType.DEVICE_OFFLINE, active=True
            ).exists()
        )

    # Device becomes offline

    def test_device_becomes_offline_after_timeout(self):
        """
        A device becomes OFFLINE when its heartbeat has expired.
        """

        now = timezone.now()

        self.device.last_seen = now - timedelta(seconds=61)

        self.device.save(update_fields=["last_seen"])

        check_device_timeout(device=self.device, timeout_seconds=60, now=now)

        self.device.refresh_from_db()

        # Device should now be offline.
        self.assertEqual(self.device.status, DeviceStatus.OFFLINE)

        # An offline alert should exist.
        alert = DeviceAlert.objects.get(
            device=self.device, alert_type=AlertType.DEVICE_OFFLINE, active=True
        )

        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)

        self.assertIn("offline", alert.message.lower())

    # Offline alert is not duplicated

    def test_offline_alert_is_not_duplicated(self):
        """
        Repeated timeout checks must not create duplicate active
        offline alerts.
        """

        now = timezone.now()

        self.device.last_seen = now - timedelta(seconds=61)

        self.device.save(update_fields=["last_seen"])

        # First timeout check.
        check_device_timeout(device=self.device, timeout_seconds=60, now=now)

        # Second timeout check.
        check_device_timeout(device=self.device, timeout_seconds=60, now=now)

        active_alerts = DeviceAlert.objects.filter(
            device=self.device, alert_type=AlertType.DEVICE_OFFLINE, active=True
        )

        self.assertEqual(active_alerts.count(), 1)

    # Never-seen device remains UNKNOWN

    def test_device_without_last_seen_remains_unknown(self):
        """
        A device that has never communicated remains UNKNOWN.

        We don't have enough information to say that it is offline.
        """

        self.device.status = DeviceStatus.UNKNOWN
        self.device.last_seen = None

        self.device.save(update_fields=["status", "last_seen"])

        check_device_timeout(device=self.device, timeout_seconds=60)

        self.device.refresh_from_db()

        self.assertEqual(self.device.status, DeviceStatus.UNKNOWN)

        self.assertFalse(
            DeviceAlert.objects.filter(
                device=self.device, alert_type=AlertType.DEVICE_OFFLINE, active=True
            ).exists()
        )


class RetentionServiceTests(TestCase):
    """
    Tests for monitoring/services/retention.py's stale-alert auto-resolve
    and detection retention -- these guard the exact behaviour requested:
    an error alert or detection no longer being reported on MQTT should
    not stay "active"/visible forever.
    """

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
            status=DeviceStatus.ONLINE,
        )

        cls.camera = Camera.objects.create(
            device=cls.device,
            camera_identifier="AXIS-1",
            channel=1,
            name="Front door",
            status=CameraStatus.ONLINE,
        )

    def test_create_device_issue_alert_bumps_last_seen_on_reuse(self):
        from monitoring.services.device_health import create_device_issue_alert

        alert = create_device_issue_alert(
            device=self.device, issue_name="disk_full", payload={}
        )
        alert.last_seen_at = timezone.now() - timedelta(hours=10)
        alert.save(update_fields=["last_seen_at"])

        # Same issue reported again -- must reuse the row (not duplicate
        # it) and refresh last_seen_at.
        reused = create_device_issue_alert(
            device=self.device, issue_name="disk_full", payload={}
        )

        self.assertEqual(alert.id, reused.id)
        self.assertEqual(
            DeviceAlert.objects.filter(
                device=self.device, alert_type=AlertType.DEVICE_ERROR
            ).count(),
            1,
        )
        reused.refresh_from_db()
        self.assertGreater(reused.last_seen_at, timezone.now() - timedelta(minutes=1))

    def test_resolve_stale_alerts_resolves_alert_not_reseen_on_mqtt(self):
        from monitoring.services.device_health import create_device_issue_alert
        from monitoring.services.retention import resolve_stale_alerts

        stale_alert = create_device_issue_alert(
            device=self.device, issue_name="disk_full", payload={}
        )
        stale_alert.last_seen_at = timezone.now() - timedelta(hours=25)
        stale_alert.save(update_fields=["last_seen_at"])

        fresh_alert = create_device_issue_alert(
            device=self.device, issue_name="high_temp", payload={}
        )
        # last_seen_at defaults to now() -- still well within 24h.

        resolved_count = resolve_stale_alerts(stale_after_hours=24)

        self.assertEqual(resolved_count, 1)

        stale_alert.refresh_from_db()
        self.assertFalse(stale_alert.active)
        self.assertIsNotNone(stale_alert.resolved_at)

        fresh_alert.refresh_from_db()
        self.assertTrue(fresh_alert.active)

    def test_resolve_stale_alerts_does_not_touch_offline_alerts(self):
        """
        A device that is still genuinely offline must not be auto-resolved
        just because time passed -- only issue-style alerts (DEVICE_ERROR/
        CAMERA_ERROR) are eligible for time-based staleness.
        """

        from monitoring.services.device_health import create_offline_alert
        from monitoring.services.retention import resolve_stale_alerts

        offline_alert = create_offline_alert(self.device)
        DeviceAlert.objects.filter(id=offline_alert.id).update(
            last_seen_at=timezone.now() - timedelta(days=5)
        )

        resolve_stale_alerts(stale_after_hours=24)

        offline_alert.refresh_from_db()
        self.assertTrue(offline_alert.active)

    def test_detection_creates_a_new_row_every_time(self):
        """
        Regression test: detections used to dedupe onto a single active
        CameraAlert row (like problem alerts do), so repeated detections
        silently overwrote each other instead of building a history.
        """

        from monitoring.services.camera_monitor import process_camera_detection

        process_camera_detection(
            camera=self.camera,
            payload={"action_code": "SMOKE", "class_label": "smoke", "confidence": 0.9},
        )
        process_camera_detection(
            camera=self.camera,
            payload={"action_code": "SMOKE", "class_label": "smoke", "confidence": 0.95},
        )

        self.assertEqual(
            CameraAlert.objects.filter(
                camera=self.camera, alert_type=CameraAlertType.CAMERA_ALERT
            ).count(),
            2,
        )

    def test_delete_old_detections_removes_only_old_rows(self):
        from monitoring.services.retention import delete_old_detections

        old = CameraAlert.objects.create(
            camera=self.camera,
            alert_type=CameraAlertType.CAMERA_ALERT,
            severity=AlertSeverity.WARNING,
            message="old detection",
        )
        CameraAlert.objects.filter(id=old.id).update(
            created_at=timezone.now() - timedelta(days=11)
        )

        recent = CameraAlert.objects.create(
            camera=self.camera,
            alert_type=CameraAlertType.CAMERA_ALERT,
            severity=AlertSeverity.WARNING,
            message="recent detection",
        )

        deleted = delete_old_detections(retention_days=10)

        self.assertEqual(deleted, 1)
        self.assertFalse(CameraAlert.objects.filter(id=old.id).exists())
        self.assertTrue(CameraAlert.objects.filter(id=recent.id).exists())

    def test_get_camera_detections_excludes_rows_past_retention_window(self):
        from monitoring.services.dashboard import get_camera_detections

        old = CameraAlert.objects.create(
            camera=self.camera,
            alert_type=CameraAlertType.CAMERA_ALERT,
            severity=AlertSeverity.WARNING,
            message="old detection",
        )
        CameraAlert.objects.filter(id=old.id).update(
            created_at=timezone.now() - timedelta(days=11)
        )

        CameraAlert.objects.create(
            camera=self.camera,
            alert_type=CameraAlertType.CAMERA_ALERT,
            severity=AlertSeverity.WARNING,
            message="recent detection",
        )

        with self.settings(DETECTION_RETENTION_DAYS=10):
            results = get_camera_detections(limit=50)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["message"], "recent detection")

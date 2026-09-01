"""
Tests for monitoring/services/retention.py.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from countries.models import Country
from customers.models import Customer
from devices.models import Device, DeviceStatus, DeviceType
from locations.models import Location
from monitoring.models import DeviceHeartbeat
from monitoring.services.retention import delete_old_heartbeats


class DeleteOldHeartbeatsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        country = Country.objects.create(name="Portugal", code="PT")
        customer = Customer.objects.create(country=country, name="aitecserv")
        location = Location.objects.create(customer=customer, name="office2")

        cls.device = Device.objects.create(
            location=location,
            name="Edge 01",
            mqtt_identifier="edge-01",
            serial_number="EDGE-001",
            device_type=DeviceType.EDGE,
            status=DeviceStatus.UNKNOWN,
        )

    def _create_heartbeat(self, received_at):
        heartbeat = DeviceHeartbeat.objects.create(device=self.device)
        # received_at is auto_now_add, so it has to be overwritten after
        # creation with a plain queryset update.
        DeviceHeartbeat.objects.filter(pk=heartbeat.pk).update(received_at=received_at)
        return heartbeat

    def test_deletes_only_heartbeats_older_than_retention_window(self):
        now = timezone.now()

        old_heartbeat = self._create_heartbeat(now - timedelta(days=30))
        recent_heartbeat = self._create_heartbeat(now - timedelta(days=1))

        deleted_count = delete_old_heartbeats(retention_days=14)

        self.assertEqual(deleted_count, 1)
        self.assertFalse(DeviceHeartbeat.objects.filter(pk=old_heartbeat.pk).exists())
        self.assertTrue(DeviceHeartbeat.objects.filter(pk=recent_heartbeat.pk).exists())

    def test_returns_zero_when_nothing_is_old_enough(self):
        self._create_heartbeat(timezone.now())

        deleted_count = delete_old_heartbeats(retention_days=14)

        self.assertEqual(deleted_count, 0)
        self.assertEqual(DeviceHeartbeat.objects.count(), 1)

    def test_deletes_across_multiple_batches(self):
        now = timezone.now()

        for _ in range(12):
            self._create_heartbeat(now - timedelta(days=30))

        deleted_count = delete_old_heartbeats(retention_days=14, batch_size=5)

        self.assertEqual(deleted_count, 12)
        self.assertEqual(DeviceHeartbeat.objects.count(), 0)

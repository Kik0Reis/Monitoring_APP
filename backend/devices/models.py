from django.db import models

from core.models import TimeStampedModel
from locations.models import Location


class DeviceStatus(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    OFFLINE = "OFFLINE", "Offline"
    UNKNOWN = "UNKNOWN", "Unknown"


class DeviceType(models.TextChoices):
    EDGE = "EDGE", "Edge Device"


class Device(TimeStampedModel):
    """The on-site box a customer's cameras plug into.

    status = health of the box itself. Internal services (detectorapi,
    detector, idmr, ...) live in component_statuses -- one can be down
    while the box is still reachable.
    """

    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="devices"
    )

    name = models.CharField(max_length=150)
    mqtt_identifier = models.CharField(max_length=150, db_index=True)
    serial_number = models.CharField(max_length=100, unique=True, db_index=True)

    status = models.CharField(
        max_length=10, choices=DeviceStatus.choices, default=DeviceStatus.UNKNOWN
    )

    last_seen = models.DateTimeField(null=True, blank=True)

    # did this device show up in the last broker reconciliation? not
    # time-based like status, only flips False when a full reconcile cycle
    # genuinely missed it (see monitoring/services/mqtt_reconciliation.py)
    on_mqtt = models.BooleanField(default=True)

    # per-service health, e.g. {"detectorapi": {"status": "up", ...}, "detector": {...}}
    component_statuses = models.JSONField(default=dict, blank=True)

    health_data = models.JSONField(default=dict, blank=True)

    # OS/CPU/RAM/GPU/IP from aiaction/.../info/edge-device, display-only
    system_info = models.JSONField(default=dict, blank=True)

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.EDGE,
        editable=False,
    )

    active = models.BooleanField(default=True)

    # set for devices auto-created from MQTT traffic, just a UI flag so
    # a human can confirm/rename and fill in the real serial number
    pending_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Device"
        verbose_name_plural = "Devices"

        constraints = [
            models.UniqueConstraint(
                fields=["location", "name"], name="unique_device_name_per_location"
            ),
            # unique per location only, not globally -- two customers can
            # both have a device their MQTT topic calls "01" (see mqtt/provisioning.py)
            models.UniqueConstraint(
                fields=["location", "mqtt_identifier"],
                name="unique_device_mqtt_identifier_per_location",
            ),
        ]

    def __str__(self):
        return self.name

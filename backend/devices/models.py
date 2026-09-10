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
    """
    An Edge device — the box on-site that a customer's cameras plug into.

    Device.status is the health of the Edge box itself. Its internal
    services (detectorapi, detector, idmr, ...) are tracked separately in
    component_statuses, since one can be down while the box overall is
    still reachable.
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

    # Whether this device showed up the last time the MQTT subscriber
    # reconciled its known devices against the broker (see
    # monitoring/services/mqtt_reconciliation.py). Unlike `status`, this is
    # never time-based -- it only flips to False when a full reconcile
    # cycle genuinely didn't see this device, which is what lets a device
    # be deleted with confidence after e.g. a bulk country delete.
    on_mqtt = models.BooleanField(default=True)

    # Health of each internal service the Edge box runs, e.g.:
    #
    # {
    #     "detectorapi": {"status": "up", "initialized": true, "configs_loaded": true},
    #     "detector": {"status": "up", "unhealthy_cameras": []},
    #     "idmr": {"status": "up", "config_loaded": true, "unhealthy_cameras": []}
    # }
    component_statuses = models.JSONField(default=dict, blank=True)

    health_data = models.JSONField(default=dict, blank=True)

    # Hardware/system info reported on aiaction/.../info/edge-device, e.g.
    # OS, CPU/RAM/GPU specs, IP address. Purely informational -- shown on
    # the device detail page, never used for status/health logic.
    system_info = models.JSONField(default=dict, blank=True)

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.EDGE,
        editable=False,
    )

    active = models.BooleanField(default=True)

    # True for devices auto-created from an MQTT topic that didn't match
    # any existing device. Fully functional either way — this is just a
    # UI flag so a human can confirm/rename it and fill in its real
    # serial number (auto-created devices get a placeholder).
    pending_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Device"
        verbose_name_plural = "Devices"

        constraints = [
            models.UniqueConstraint(
                fields=["location", "name"], name="unique_device_name_per_location"
            ),
            # mqtt_identifier is only guaranteed unique WITHIN a location,
            # not globally — two different customers can legitimately
            # both have a device whose MQTT topic calls it "01". Messages
            # are routed using the full country/client/installation/
            # device_id path (see mqtt/provisioning.py), never a bare
            # device_id lookup.
            models.UniqueConstraint(
                fields=["location", "mqtt_identifier"],
                name="unique_device_mqtt_identifier_per_location",
            ),
        ]

    def __str__(self):
        return self.name

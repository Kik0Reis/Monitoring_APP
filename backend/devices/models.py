# database model of a device

from django.db import models

from core.models import TimeStampedModel
from locations.models import Location


# possible statuses of a device
class DeviceStatus(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    OFFLINE = "OFFLINE", "Offline"
    UNKNOWN = "UNKNOWN", "Unknown"


# kinds of device
class DeviceType(models.TextChoices):
    EDGE = "EDGE", "Edge Device"


# the on-site box where the cameras of a customer are connected
class Device(TimeStampedModel):
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

    # True when the device was seen in the last mqtt reconciliation, it is not time based
    on_mqtt = models.BooleanField(default=True)

    # status of each internal service, for example {"detectorapi": {"status": "up"}}
    component_statuses = models.JSONField(default=dict, blank=True)

    health_data = models.JSONField(default=dict, blank=True)

    # os, cpu, ram, gpu and ip from info/edge-device, only shown in the interface
    system_info = models.JSONField(default=dict, blank=True)

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.EDGE,
        editable=False,
    )

    active = models.BooleanField(default=True)

    # True for devices created automatically from mqtt, a person can confirm them and add the real serial number
    pending_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Device"
        verbose_name_plural = "Devices"

        constraints = [
            models.UniqueConstraint(
                fields=["location", "name"], name="unique_device_name_per_location"
            ),
            # unique per location only, two customers can both have a device called 01
            models.UniqueConstraint(
                fields=["location", "mqtt_identifier"],
                name="unique_device_mqtt_identifier_per_location",
            ),
        ]

    # returns the device name
    def __str__(self):
        return self.name

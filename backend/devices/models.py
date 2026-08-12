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
    Represents an Edge device.

    An Edge device can have multiple cameras connected to it.
    """

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="devices",
    )

    name = models.CharField(
        max_length=150,
    )

    mqtt_identifier = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
    )

    serial_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=10,
        choices=DeviceStatus.choices,
        default=DeviceStatus.UNKNOWN,
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
    )

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.EDGE,
        editable=False,
    )

    active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Device"
        verbose_name_plural = "Devices"

        constraints = [
            models.UniqueConstraint(
                fields=["location", "name"],
                name="unique_device_name_per_location",
            ),
        ]

    def __str__(self):
        return self.name
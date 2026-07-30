from django.db import models

from core.models import TimeStampedModel
from locations.models import Location



# Enum for device status
class DeviceStatus(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    OFFLINE = "OFFLINE", "Offline"
    UNKNOWN = "UNKNOWN", "Unknown"

# Enum for device type
class DeviceType(models.TextChoices):
    CAMERA = "CAMERA", "Camera"
    EDGE = "EDGE", "Edge Device"

# Model for the device
# it has a name, a mqtt_identifier, a serial_number, a status, a last_seen and an active status and a foreign key to the location model
class Device(TimeStampedModel):
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="devices",
    )

    name = models.CharField(max_length=150)

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
        default=DeviceType.CAMERA,
    )

    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Device"
        verbose_name_plural = "Devices"

    def __str__(self):
        return self.name
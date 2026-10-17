# database model of a camera

from django.db import models

from core.models import TimeStampedModel
from devices.models import Device


# possible statuses of a camera
class CameraStatus(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    OFFLINE = "OFFLINE", "Offline"
    UNKNOWN = "UNKNOWN", "Unknown"


# a camera connected to an edge device, a device can have several
class Camera(TimeStampedModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="cameras")

    name = models.CharField(max_length=150)

    camera_identifier = models.CharField(max_length=150, db_index=True)

    channel = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=10, choices=CameraStatus.choices, default=CameraStatus.UNKNOWN
    )

    last_seen = models.DateTimeField(null=True, blank=True)

    # True when the camera was seen in the last mqtt reconciliation, it is not time based
    on_mqtt = models.BooleanField(default=True)

    # identity info from info/cameras, only filled automatically while pending_review is True
    serial_number = models.CharField(max_length=100, blank=True, default="")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # breakdown of the components for this camera, taken from the health messages
    # for example {"detectorapi": {"stage": "idle"}, "detector": {"healthy": true}}
    health_data = models.JSONField(default=dict, blank=True)

    # license info from info/licenses (licensed, status, dates, days_left, ...)
    license_data = models.JSONField(default=dict, blank=True)

    active = models.BooleanField(default=True)

    # True for cameras created automatically from mqtt, a person can confirm them or rename them
    pending_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Camera"
        verbose_name_plural = "Cameras"

        constraints = [
            models.UniqueConstraint(
                fields=["device", "camera_identifier", "channel"],
                name="unique_camera_per_device_channel",
            ),
            models.UniqueConstraint(
                fields=["device", "name"], name="unique_camera_name_per_device"
            ),
        ]

    # returns the camera name
    def __str__(self):
        return f"{self.name} ({self.camera_identifier}/ch{self.channel})"

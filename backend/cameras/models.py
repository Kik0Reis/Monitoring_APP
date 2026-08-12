from django.db import models

from core.models import TimeStampedModel
from devices.models import Device


class CameraStatus(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    OFFLINE = "OFFLINE", "Offline"
    UNKNOWN = "UNKNOWN", "Unknown"


class Camera(TimeStampedModel):
    """
    Represents a camera connected to an Edge device.

    One Edge Device can have multiple Cameras.
    """

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="cameras",
    )

    name = models.CharField(
        max_length=150,
    )

    camera_identifier = models.CharField(
        max_length=150,
        db_index=True,
    )

    channel = models.PositiveIntegerField(
        default=1,
    )

    status = models.CharField(
        max_length=10,
        choices=CameraStatus.choices,
        default=CameraStatus.UNKNOWN,
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
    )

    active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Camera"
        verbose_name_plural = "Cameras"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "device",
                    "camera_identifier",
                    "channel",
                ],
                name="unique_camera_per_device_channel",
            ),
            models.UniqueConstraint(
                fields=[
                    "device",
                    "name",
                ],
                name="unique_camera_name_per_device",
            ),
        ]

    def __str__(self):
        return (
            f"{self.name} "
            f"({self.camera_identifier}/ch{self.channel})"
        )
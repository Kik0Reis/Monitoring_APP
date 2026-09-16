from django.db import models

from core.models import TimeStampedModel
from devices.models import Device


class CameraStatus(models.TextChoices):
    ONLINE = "ONLINE", "Online"
    OFFLINE = "OFFLINE", "Offline"
    UNKNOWN = "UNKNOWN", "Unknown"


class Camera(TimeStampedModel):
    """A camera attached to an Edge device. One device can have several."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="cameras")

    name = models.CharField(max_length=150)

    camera_identifier = models.CharField(max_length=150, db_index=True)

    channel = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=10, choices=CameraStatus.choices, default=CameraStatus.UNKNOWN
    )

    last_seen = models.DateTimeField(null=True, blank=True)

    # Whether this camera showed up the last time the MQTT subscriber
    # reconciled its known cameras against the broker (see
    # monitoring/services/mqtt_reconciliation.py). Unlike `status`, this is
    # never time-based -- it only flips to False when a full reconcile
    # cycle genuinely didn't see this camera.
    on_mqtt = models.BooleanField(default=True)

    # Identity info reported on aiaction/.../info/cameras. Blank until
    # that message arrives; only auto-filled while pending_review=True so
    # a human's edits are never overwritten by MQTT traffic.
    serial_number = models.CharField(max_length=100, blank=True, default="")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Per-component breakdown for THIS camera specifically, extracted from
    # the detectorapi/detector/idmr health messages (which report a dict
    # keyed by "{camera_id}_ch{channel}"). E.g.:
    #   {"detectorapi": {"stage": "idle", ...}, "detector": {"healthy": true, ...}}
    health_data = models.JSONField(default=dict, blank=True)

    # License status reported on aiaction/.../info/licenses, keyed by
    # nothing in particular -- it's just the raw entry for this camera
    # (licensed, status, begin_date, end_date, days_left, last_validation_*).
    license_data = models.JSONField(default=dict, blank=True)

    active = models.BooleanField(default=True)

    # True for cameras auto-created from an MQTT topic (the device's
    # ".../cameras" status list) that didn't match any existing camera.
    # Fully functional either way — this is just a UI flag so a human can
    # confirm it / give it a nicer name.
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

    def __str__(self):
        return f"{self.name} ({self.camera_identifier}/ch{self.channel})"

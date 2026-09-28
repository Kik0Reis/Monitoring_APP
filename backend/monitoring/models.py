from django.db import models
from django.utils import timezone

from devices.models import Device, DeviceStatus


class DeviceHeartbeat(models.Model):
    """
    One heartbeat/health message received from a device over MQTT.

    The Device model always holds the current state; this table is the
    history of every message that led up to it.
    """

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="heartbeats")

    # When our backend received the MQTT message.
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Timestamp the device itself put in the payload — can differ from
    # received_at if the device's clock is off or the message was delayed.
    timestamp = models.DateTimeField(null=True, blank=True)

    cpu = models.FloatField(null=True, blank=True)
    memory = models.FloatField(null=True, blank=True)
    storage = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)

    # The full MQTT payload, kept as-is. Health messages carry nested
    # per-component info (edge-device, detector, idmr, detectorapi, ...)
    # that isn't worth its own column until we know what the dashboard
    # actually needs from it.
    raw_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "Device Heartbeat"
        verbose_name_plural = "Device Heartbeats"

    def __str__(self):
        return f"{self.device.name} - {self.received_at}"


class DeviceStatusHistory(models.Model):
    """
    A log of a device's status transitions (UNKNOWN -> ONLINE -> OFFLINE,
    etc). The Device model only holds the current status — this is what
    lets you see when and how often it's been flapping.
    """

    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="status_history"
    )

    old_status = models.CharField(max_length=10, choices=DeviceStatus.choices)
    new_status = models.CharField(max_length=10, choices=DeviceStatus.choices)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "Device Status History"
        verbose_name_plural = "Device Status Histories"

    def __str__(self):
        return f"{self.device.name}: {self.old_status} -> {self.new_status}"


class AlertSeverity(models.TextChoices):
    """How urgent an alert is, for sorting/coloring it on the dashboard."""

    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    CRITICAL = "CRITICAL", "Critical"


class AlertType(models.TextChoices):
    """The kinds of problem a DeviceAlert can represent."""

    DEVICE_OFFLINE = "DEVICE_OFFLINE", "Device Offline"
    DEVICE_HEALTH = "DEVICE_HEALTH", "Device Health"
    DEVICE_ERROR = "DEVICE_ERROR", "Device Error"
    MQTT_ERROR = "MQTT_ERROR", "MQTT Error"
    SYSTEM_ERROR = "SYSTEM_ERROR", "System Error"


class DeviceAlert(models.Model):
    """
    A problem raised by the monitoring logic for an Edge device — e.g. it
    stopped sending heartbeats, reported an unhealthy component, or hit
    an MQTT error. Alerts are created by the monitoring services, never
    directly by the MQTT parser.
    """

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="alerts")

    alert_type = models.CharField(max_length=30, choices=AlertType.choices)

    severity = models.CharField(
        max_length=10, choices=AlertSeverity.choices, default=AlertSeverity.WARNING
    )

    message = models.TextField()

    # Stays True until whatever caused the alert is resolved.
    active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Set only when a human resolved this from the dashboard/alerts/device
    # detail UI (as opposed to the monitoring services resolving it
    # automatically because the underlying problem genuinely cleared).
    # This is what lets a manual resolve actually "stick": as long as this
    # is set, the create_*_alert() helpers in device_health.py keep this
    # same row resolved instead of immediately raising a fresh one for the
    # same still-ongoing problem, and only clear it once there's a real
    # "back to normal" signal (see resolve_offline_alerts/
    # resolve_health_alerts) proving this is a genuinely new occurrence.
    manually_resolved_at = models.DateTimeField(null=True, blank=True)

    # Bumped every time this same alert is re-reported over MQTT (see
    # create_device_issue_alert). DEVICE_OFFLINE/DEVICE_HEALTH resolve
    # immediately on the matching "back to normal" signal, but free-form
    # DEVICE_ERROR issues have no such signal -- an issue_name simply
    # stops being republished once fixed. The stale-alert cleanup job
    # (monitoring.services.retention.resolve_stale_alerts) auto-resolves
    # any active alert whose last_seen_at is older than
    # settings.ALERT_STALE_HOURS, so alerts no longer on MQTT don't stay
    # "active" forever.
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    # The MQTT payload that triggered this, if there was one — handy for
    # debugging without having to dig through logs.
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Device Alert"
        verbose_name_plural = "Device Alerts"

    def __str__(self):
        return f"{self.device.name} - {self.alert_type} - {self.severity}"


class CameraAlertType(models.TextChoices):
    CAMERA_ALERT = "CAMERA_ALERT", "Camera Alert"
    CAMERA_ERROR = "CAMERA_ERROR", "Camera Error"
    CAMERA_OFFLINE = "CAMERA_OFFLINE", "Camera Offline"


class CameraAlert(models.Model):
    """
    A problem or detection reported by a single camera. Kept separate
    from DeviceAlert because one Edge device can have several cameras,
    each with its own alert history.
    """

    camera = models.ForeignKey(
        "cameras.Camera", on_delete=models.CASCADE, related_name="alerts"
    )

    alert_type = models.CharField(max_length=30, choices=CameraAlertType.choices)

    severity = models.CharField(
        max_length=10, choices=AlertSeverity.choices, default=AlertSeverity.WARNING
    )

    message = models.TextField()
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # See DeviceAlert.manually_resolved_at -- same "resolve actually
    # sticks" mechanism, for CAMERA_OFFLINE (and CAMERA_ERROR, once
    # something creates those). Not used for CAMERA_ALERT (real
    # detections): once one is manually resolved it's simply gone, there's
    # no "same occurrence" to keep suppressing since each detection is
    # already its own row.
    manually_resolved_at = models.DateTimeField(null=True, blank=True)

    # See DeviceAlert.last_seen_at -- same mechanism, kept in step so
    # CAMERA_ERROR behaves the same way if/when a per-camera issue topic
    # is added. Not used for CAMERA_ALERT (real detections): those never
    # reuse a row (see camera_monitor.process_camera_detection), so
    # last_seen_at just equals created_at for them and is harmless.
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Camera Alert"
        verbose_name_plural = "Camera Alerts"

    def __str__(self):
        return f"{self.camera.name} - {self.alert_type} - {self.severity}"

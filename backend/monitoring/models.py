# database models for heartbeats, status history and alerts of devices and cameras

from django.db import models
from django.utils import timezone

from devices.models import Device, DeviceStatus


# a heartbeat or health message received from a device over mqtt
class DeviceHeartbeat(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="heartbeats")

    # when the backend received the mqtt message
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # time written by the device in the payload, can differ from received_at if its clock is wrong
    timestamp = models.DateTimeField(null=True, blank=True)

    cpu = models.FloatField(null=True, blank=True)
    memory = models.FloatField(null=True, blank=True)
    storage = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)

    # the full mqtt payload as received, it has the nested info of each component
    raw_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "Device Heartbeat"
        verbose_name_plural = "Device Heartbeats"

    # returns the device name and the received time
    def __str__(self):
        return f"{self.device.name} - {self.received_at}"


# a log of the status changes of a device
class DeviceStatusHistory(models.Model):
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

    # returns the device name and the status change
    def __str__(self):
        return f"{self.device.name}: {self.old_status} -> {self.new_status}"


# how urgent an alert is
class AlertSeverity(models.TextChoices):
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    CRITICAL = "CRITICAL", "Critical"


# the kinds of problem a device alert can be
class AlertType(models.TextChoices):
    DEVICE_OFFLINE = "DEVICE_OFFLINE", "Device Offline"
    DEVICE_HEALTH = "DEVICE_HEALTH", "Device Health"
    DEVICE_ERROR = "DEVICE_ERROR", "Device Error"
    MQTT_ERROR = "MQTT_ERROR", "MQTT Error"
    SYSTEM_ERROR = "SYSTEM_ERROR", "System Error"


# a problem found for a device, for example it went offline
class DeviceAlert(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="alerts")

    alert_type = models.CharField(max_length=30, choices=AlertType.choices)

    severity = models.CharField(
        max_length=10, choices=AlertSeverity.choices, default=AlertSeverity.WARNING
    )

    message = models.TextField()

    # stays True until the cause of the alert is resolved
    active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # set only when a person resolved the alert in the interface
    # while it is set, the same alert stays resolved instead of being created again for the same ongoing problem
    manually_resolved_at = models.DateTimeField(null=True, blank=True)

    # updated every time the same alert is reported again over mqtt
    # the cleanup job resolves alerts not seen for ALERT_STALE_HOURS
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    # the mqtt payload that created the alert, useful for debugging
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Device Alert"
        verbose_name_plural = "Device Alerts"

    # returns the device name and the alert type
    def __str__(self):
        return f"{self.device.name} - {self.alert_type} - {self.severity}"


# the kinds of event a camera alert can be
class CameraAlertType(models.TextChoices):
    CAMERA_ALERT = "CAMERA_ALERT", "Camera Alert"
    CAMERA_ERROR = "CAMERA_ERROR", "Camera Error"
    CAMERA_OFFLINE = "CAMERA_OFFLINE", "Camera Offline"


# a problem or detection reported by one camera
class CameraAlert(models.Model):
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

    # same as DeviceAlert.manually_resolved_at, not used for detections
    manually_resolved_at = models.DateTimeField(null=True, blank=True)

    # same as DeviceAlert.last_seen_at, for detections it is equal to created_at
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Camera Alert"
        verbose_name_plural = "Camera Alerts"

    # returns the camera name and the alert type
    def __str__(self):
        return f"{self.camera.name} - {self.alert_type} - {self.severity}"

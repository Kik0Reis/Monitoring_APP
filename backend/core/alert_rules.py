from django.conf import settings
from django.utils import timezone

DEVICE_ERROR_ALERT_TYPES = ["DEVICE_ERROR", "MQTT_ERROR", "SYSTEM_ERROR"]
CAMERA_ERROR_ALERT_TYPES = ["CAMERA_ERROR"]
ERROR_ALERT_TYPES = DEVICE_ERROR_ALERT_TYPES + CAMERA_ERROR_ALERT_TYPES

OFFLINE_ALERT_TYPES = {"DEVICE_OFFLINE", "CAMERA_OFFLINE"}
HEALTH_ALERT_TYPES = {"DEVICE_HEALTH"}


# returns the category of an alert type: offline, health or error
def alert_category(alert_type):
    if alert_type in OFFLINE_ALERT_TYPES:
        return "offline"
    if alert_type in HEALTH_ALERT_TYPES:
        return "health"
    return "error"


# returns the moment before which an error alert is too old to still show
def error_alert_cutoff():
    return timezone.now() - timezone.timedelta(hours=settings.ALERT_VISIBLE_HOURS)


# returns the moment before which a detection is too old to still show
def detection_cutoff():
    return timezone.now() - timezone.timedelta(hours=settings.DETECTION_VISIBLE_HOURS)


# returns True when an alert should still be shown: only error alerts expire
def is_alert_visible(alert_type, created_at):
    return alert_type not in ERROR_ALERT_TYPES or created_at >= error_alert_cutoff()


# turns an alert into the small dict the device and camera pages show
def alert_summary(alert):
    return {
        "id": alert.id,
        "alert_type": alert.alert_type,
        "category": alert_category(alert.alert_type),
        "severity": alert.severity,
        "message": alert.message,
        "active": alert.active,
        "created_at": alert.created_at,
        "resolved_at": alert.resolved_at,
    }

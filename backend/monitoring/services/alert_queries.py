from django.db.models import Q

from core.alert_rules import (
    CAMERA_ERROR_ALERT_TYPES,
    DEVICE_ERROR_ALERT_TYPES,
    ERROR_ALERT_TYPES,
    detection_cutoff,
    error_alert_cutoff,
)
from monitoring.models import AlertType, CameraAlert, CameraAlertType, DeviceAlert
from monitoring.services.scope import active_camera_q, active_device_q

# matches error alerts older than the visibility window, use prefix to reach them from another model
def stale_error_alert_q(prefix=""):
    return Q(**{f"{prefix}alert_type__in": ERROR_ALERT_TYPES}) & Q(
        **{f"{prefix}created_at__lt": error_alert_cutoff()}
    )


# returns the (device alerts, camera alerts) querysets for the problems lists
def problem_querysets(unresolved_only=True, category=None, hide_inactive=False):
    device_alerts = DeviceAlert.objects.select_related("device", "device__location")
    camera_alerts = CameraAlert.objects.filter(
        alert_type__in=[CameraAlertType.CAMERA_ERROR, CameraAlertType.CAMERA_OFFLINE]
    ).select_related("camera", "camera__device", "camera__device__location")

    if unresolved_only:
        device_alerts = device_alerts.filter(active=True).exclude(stale_error_alert_q())
        camera_alerts = camera_alerts.filter(active=True).exclude(stale_error_alert_q())

    if hide_inactive:
        device_alerts = device_alerts.filter(active_device_q("device__"))
        camera_alerts = camera_alerts.filter(active_camera_q("camera__"))

    if category == "offline":
        device_alerts = device_alerts.filter(alert_type=AlertType.DEVICE_OFFLINE)
        camera_alerts = camera_alerts.filter(alert_type=CameraAlertType.CAMERA_OFFLINE)
    elif category == "health":
        device_alerts = device_alerts.filter(alert_type=AlertType.DEVICE_HEALTH)
        camera_alerts = camera_alerts.none()
    elif category == "error":
        device_alerts = device_alerts.filter(alert_type__in=DEVICE_ERROR_ALERT_TYPES)
        camera_alerts = camera_alerts.filter(alert_type__in=CAMERA_ERROR_ALERT_TYPES)

    return device_alerts, camera_alerts


# returns the queryset of detections that are still active and inside the visibility window
def detections_queryset(hide_inactive=False):
    detections = CameraAlert.objects.filter(
        alert_type=CameraAlertType.CAMERA_ALERT,
        created_at__gte=detection_cutoff(),
        active=True,
    ).select_related("camera", "camera__device", "camera__device__location")

    if hide_inactive:
        detections = detections.filter(active_camera_q("camera__"))

    return detections

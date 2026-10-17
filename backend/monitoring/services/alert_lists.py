from core.alert_rules import alert_category
from monitoring.services.alert_queries import detections_queryset, problem_querysets

DEVICE_ALERT_LABELS = {
    "DEVICE_OFFLINE": "Offline",
    "DEVICE_HEALTH": "Health",
    "DEVICE_ERROR": "Device",
    "MQTT_ERROR": "MQTT",
    "SYSTEM_ERROR": "System",
}

CAMERA_ALERT_LABELS = {
    "CAMERA_ALERT": "Camera",
    "CAMERA_ERROR": "Camera Error",
    "CAMERA_OFFLINE": "Camera Offline",
}


# turns device alerts into plain dicts for the API
def serialize_device_alerts(device_alerts):
    alerts = []

    for alert in device_alerts:
        location = alert.device.location

        alerts.append({
            "id": f"device-{alert.id}",
            "type": DEVICE_ALERT_LABELS.get(alert.alert_type, "Device"),
            "alert_type": alert.alert_type,
            "category": alert_category(alert.alert_type),
            "severity": alert.severity,
            "device_id": alert.device.id,
            "device_name": alert.device.name,
            "location_id": location.id if location else None,
            "location_name": location.name if location else None,
            "camera_id": None,
            "camera_name": None,
            "message": alert.message,
            "active": alert.active,
            "created_at": alert.created_at,
        })

    return alerts


# turns camera alerts and detections into plain dicts for the API
def serialize_camera_alerts(camera_alerts):
    alerts = []

    for alert in camera_alerts:
        camera = alert.camera
        device = camera.device
        location = device.location if device else None
        payload = alert.raw_payload if isinstance(alert.raw_payload, dict) else {}

        alerts.append({
            "id": f"camera-{alert.id}",
            "type": CAMERA_ALERT_LABELS.get(alert.alert_type, "Camera"),
            "alert_type": alert.alert_type,
            "category": alert_category(alert.alert_type),
            "severity": alert.severity,
            "device_id": device.id if device else None,
            "device_name": device.name if device else None,
            "location_id": location.id if location else None,
            "location_name": location.name if location else None,
            "camera_id": camera.id,
            "camera_name": camera.name,
            "detected": payload.get("class_label"),
            "action_code": payload.get("action_code"),
            "confidence": payload.get("confidence"),
            "message": alert.message,
            "active": alert.active,
            "created_at": alert.created_at,
        })

    return alerts


# converts the created_at datetimes to ISO strings so the list can be sent as JSON
def _stringify_dates(alerts):
    for alert in alerts:
        alert["created_at"] = alert["created_at"].isoformat()
    return alerts


# returns the newest device and camera problems merged into one list, newest first
def get_problem_alerts(limit=10, unresolved_only=True, category=None, hide_inactive=False):
    device_alerts, camera_alerts = problem_querysets(unresolved_only, category, hide_inactive)

    alerts = serialize_device_alerts(device_alerts.order_by("-created_at")[:limit])
    alerts += serialize_camera_alerts(camera_alerts.order_by("-created_at")[:limit])
    alerts.sort(key=lambda alert: alert["created_at"], reverse=True)

    return _stringify_dates(alerts[:limit])


# returns the newest camera detections, newest first
def get_camera_detections(limit=50, hide_inactive=False):
    detections = detections_queryset(hide_inactive).order_by("-created_at")[:limit]
    return _stringify_dates(serialize_camera_alerts(detections))


# returns how many offline problems, error problems and detections are currently visible
def get_alert_counts(hide_inactive=False):
    counts = {}

    for category in ("offline", "error"):
        device_alerts, camera_alerts = problem_querysets(
            unresolved_only=True, category=category, hide_inactive=hide_inactive
        )
        counts[category] = device_alerts.count() + camera_alerts.count()

    counts["detections"] = detections_queryset(hide_inactive).count()
    return counts

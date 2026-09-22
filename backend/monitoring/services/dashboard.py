"""Builds all the data the frontend dashboard needs. Single source of truth --
views.py just calls get_dashboard_data()."""

from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from cameras.models import Camera, CameraStatus
from devices.models import Device, DeviceStatus
from locations.models import Location
from monitoring.models import CameraAlert, CameraAlertType, DeviceAlert
from monitoring.services.device_health import is_component_healthy


def get_dashboard_summary():
    """Return the top-line device/camera counts shown at the top of the dashboard."""

    devices = Device.objects.filter(active=True, device_type="EDGE")

    return {
        "devices": devices.count(),
        "online": devices.filter(status=DeviceStatus.ONLINE).count(),
        "offline": devices.filter(status=DeviceStatus.OFFLINE).count(),
        "unknown": devices.filter(status=DeviceStatus.UNKNOWN).count(),
        "cameras": Camera.objects.filter(active=True).count(),
    }


def get_problem_alerts(limit=10, active_only=True):
    """Device/camera health & connectivity problems, newest first.

    DeviceAlert (all types) + CameraAlert of type CAMERA_ERROR/CAMERA_OFFLINE.
    Not CAMERA_ALERT, those are real detections (see get_camera_detections).
    active_only=True naturally dedupes to one row per broken thing, since
    the alert row is reused while it stays broken rather than re-created.
    """

    device_alerts = DeviceAlert.objects.select_related("device", "device__location")

    camera_problem_alerts = CameraAlert.objects.filter(
        alert_type__in=[CameraAlertType.CAMERA_ERROR, CameraAlertType.CAMERA_OFFLINE]
    ).select_related("camera", "camera__device", "camera__device__location")

    if active_only:
        device_alerts = device_alerts.filter(active=True)
        camera_problem_alerts = camera_problem_alerts.filter(active=True)

    device_alerts = device_alerts.order_by("-created_at")[:limit]
    camera_problem_alerts = camera_problem_alerts.order_by("-created_at")[:limit]

    alerts = _serialize_device_alerts(device_alerts)
    alerts += _serialize_camera_alerts(camera_problem_alerts)

    alerts.sort(key=lambda alert: alert["created_at"], reverse=True)
    alerts = alerts[:limit]

    for alert in alerts:
        alert["created_at"] = alert["created_at"].isoformat()

    return alerts


def get_camera_detections(limit=50):
    """Most recent real-world detections (CAMERA_ALERT), newest first.

    Chronological log, not a "currently broken" list -- no active/resolved
    filtering, every detection shows. Restricted to the last
    settings.DETECTION_RETENTION_DAYS regardless of `limit`, matching what
    delete_old_detections() physically keeps (see
    monitoring/services/retention.py) -- the API never implies detections
    exist that the cleanup job has already removed.
    """

    cutoff = timezone.now() - timezone.timedelta(days=settings.DETECTION_RETENTION_DAYS)

    camera_alerts = (
        CameraAlert.objects.filter(
            alert_type=CameraAlertType.CAMERA_ALERT, created_at__gte=cutoff
        )
        .select_related("camera", "camera__device", "camera__device__location")
        .order_by("-created_at")[:limit]
    )

    alerts = _serialize_camera_alerts(camera_alerts)

    for alert in alerts:
        alert["created_at"] = alert["created_at"].isoformat()

    return alerts


def _serialize_device_alerts(device_alerts):
    """Turn a DeviceAlert queryset into the plain dict shape the dashboard/API return."""

    alert_type_labels = {
        "DEVICE_OFFLINE": "Offline",
        "DEVICE_HEALTH": "Health",
        "DEVICE_ERROR": "Device",
        "MQTT_ERROR": "MQTT",
        "SYSTEM_ERROR": "System",
    }

    alerts = []

    for alert in device_alerts:
        location = alert.device.location

        alerts.append(
            {
                "id": f"device-{alert.id}",
                "type": alert_type_labels.get(alert.alert_type, "Device"),
                "alert_type": alert.alert_type,
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
            }
        )

    return alerts


def _serialize_camera_alerts(camera_alerts):
    """Turn a CameraAlert queryset into the plain dict shape the dashboard/API return."""

    alert_type_labels = {
        "CAMERA_ALERT": "Camera",
        "CAMERA_ERROR": "Camera Error",
        "CAMERA_OFFLINE": "Camera Offline",
    }

    alerts = []

    for alert in camera_alerts:
        camera = alert.camera
        device = camera.device
        location = device.location if device else None

        alerts.append(
            {
                "id": f"camera-{alert.id}",
                "type": alert_type_labels.get(alert.alert_type, "Camera"),
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "device_id": device.id if device else None,
                "device_name": device.name if device else None,
                "location_id": location.id if location else None,
                "location_name": location.name if location else None,
                "camera_id": camera.id,
                "camera_name": camera.name,
                "message": alert.message,
                "active": alert.active,
                "created_at": alert.created_at,
            }
        )

    return alerts


# short labels for the dashboard row -- alert.message can be an arbitrary
# long string (DEVICE_ERROR forwards whatever text the edge device sent),
# the full message still shows on the device detail page
ALERT_TYPE_SHORT_LABELS = {
    "DEVICE_OFFLINE": "Offline",
    "DEVICE_HEALTH": "Health issue",
    "DEVICE_ERROR": "Error",
    "MQTT_ERROR": "MQTT error",
    "SYSTEM_ERROR": "System error",
}


def _device_has_component_problem(device):
    """Return the names of any unhealthy internal components on this device."""

    component_statuses = (
        device.component_statuses if isinstance(device.component_statuses, dict) else {}
    )

    unhealthy = []

    for component_name, component in component_statuses.items():
        if not isinstance(component, dict):
            continue

        status = str(component.get("status", "")).lower()

        if not is_component_healthy(status):
            unhealthy.append(component_name)

    return unhealthy


def get_devices_with_problems(limit=10):
    """Devices needing attention: OFFLINE/UNKNOWN, unhealthy component, or active alert."""

    devices = (
        Device.objects.filter(active=True, device_type="EDGE")
        .select_related("location")
        .prefetch_related(
            Prefetch(
                "alerts",
                queryset=DeviceAlert.objects.filter(active=True),
                to_attr="active_alerts_prefetched",
            )
        )
        .annotate(
            active_alert_count=Count(
                "alerts", filter=Q(alerts__active=True), distinct=True
            )
        )
    )

    result = []

    for device in devices:
        unhealthy_components = _device_has_component_problem(device)

        has_status_problem = device.status in (
            DeviceStatus.OFFLINE,
            DeviceStatus.UNKNOWN,
        )

        if not (
            has_status_problem or unhealthy_components or device.active_alert_count > 0
        ):
            continue

        issues = []

        if device.status == DeviceStatus.OFFLINE:
            issues.append("Device offline")
        elif device.status == DeviceStatus.UNKNOWN:
            issues.append("Status unknown")

        if unhealthy_components:
            issues.append("Unhealthy component(s): " + ", ".join(unhealthy_components))

        for alert in device.active_alerts_prefetched:
            issues.append(ALERT_TYPE_SHORT_LABELS.get(alert.alert_type, "Error"))

        result.append(
            {
                "id": device.id,
                "name": device.name,
                "status": device.status,
                "location_id": (device.location.id if device.location else None),
                "location_name": (device.location.name if device.location else None),
                "issues": issues,
                "last_seen": (
                    device.last_seen.isoformat() if device.last_seen else None
                ),
            }
        )

    # offline first, then unknown, then everything else
    status_priority = {DeviceStatus.OFFLINE: 0, DeviceStatus.UNKNOWN: 1}

    result.sort(
        key=lambda item: (
            status_priority.get(item["status"], 2),
            -len(item["issues"]),
            item["name"],
        )
    )

    return result[:limit]


def get_locations_with_problems(limit=10):
    """Locations with an offline/unknown device or camera, or an active alert.

    Each result gets a short "issues" list (e.g. "2 device(s) offline")
    instead of just a raw count.
    """

    locations = (
        Location.objects.annotate(
            offline_devices=Count(
                "devices",
                filter=Q(devices__active=True, devices__status=DeviceStatus.OFFLINE),
                distinct=True,
            ),
            unknown_devices=Count(
                "devices",
                filter=Q(devices__active=True, devices__status=DeviceStatus.UNKNOWN),
                distinct=True,
            ),
            active_device_alerts=Count(
                "devices__alerts",
                filter=Q(devices__active=True, devices__alerts__active=True),
                distinct=True,
            ),
            offline_cameras=Count(
                "devices__cameras",
                filter=Q(
                    devices__cameras__active=True,
                    devices__cameras__status=CameraStatus.OFFLINE,
                ),
                distinct=True,
            ),
            active_camera_alerts=Count(
                "devices__cameras__alerts",
                filter=Q(
                    devices__cameras__active=True, devices__cameras__alerts__active=True
                ),
                distinct=True,
            ),
        )
        .filter(
            Q(offline_devices__gt=0)
            | Q(unknown_devices__gt=0)
            | Q(active_device_alerts__gt=0)
            | Q(offline_cameras__gt=0)
            | Q(active_camera_alerts__gt=0)
        )
        .order_by("name")
    )

    result = []

    for location in locations[:limit]:

        problem_count = (
            location.offline_devices
            + location.unknown_devices
            + location.active_device_alerts
            + location.offline_cameras
            + location.active_camera_alerts
        )

        status = (
            "OFFLINE"
            if location.offline_devices > 0
            else "UNKNOWN" if location.unknown_devices > 0 else "WARNING"
        )

        issues = []

        if location.offline_devices > 0:
            issues.append(f"{location.offline_devices} device(s) offline")

        if location.unknown_devices > 0:
            issues.append(f"{location.unknown_devices} device(s) with unknown status")

        if location.offline_cameras > 0:
            issues.append(f"{location.offline_cameras} camera(s) offline")

        if location.active_device_alerts > 0:
            issues.append(f"{location.active_device_alerts} active device alert(s)")

        if location.active_camera_alerts > 0:
            issues.append(f"{location.active_camera_alerts} active camera alert(s)")

        result.append(
            {
                "id": location.id,
                "name": location.name,
                "status": status,
                "offline_devices": location.offline_devices,
                "unknown_devices": location.unknown_devices,
                "active_device_alerts": location.active_device_alerts,
                "offline_cameras": location.offline_cameras,
                "active_camera_alerts": location.active_camera_alerts,
                "problem_count": problem_count,
                "issues": issues,
            }
        )

    result.sort(
        key=lambda location: (
            location["status"] != "OFFLINE",
            -location["problem_count"],
            location["name"],
        )
    )

    return result[:limit]


def get_dashboard_data():
    """Everything the monitoring dashboard needs, in one call."""

    return {
        "summary": get_dashboard_summary(),
        "recent_problems": get_problem_alerts(limit=10, active_only=True),
        "devices_with_problems": get_devices_with_problems(),
        "locations_with_problems": get_locations_with_problems(),
        "recent_detections": get_camera_detections(limit=10),
    }

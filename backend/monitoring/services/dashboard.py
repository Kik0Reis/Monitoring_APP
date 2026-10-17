from django.db.models import Count, Prefetch, Q

from cameras.models import Camera, CameraStatus
from core.alert_rules import CAMERA_ERROR_ALERT_TYPES, DEVICE_ERROR_ALERT_TYPES
from devices.models import Device, DeviceStatus
from locations.models import Location
from monitoring.models import DeviceAlert
from monitoring.services.alert_lists import (
    get_alert_counts,
    get_camera_detections,
    get_problem_alerts,
)
from monitoring.services.alert_queries import stale_error_alert_q
from monitoring.services.device_health import is_component_healthy
from monitoring.services.scope import (
    active_camera_q,
    active_device_q,
    active_location_q,
)

# rows shown in the small dashboard previews and in the full problem lists
DASHBOARD_PREVIEW_ROWS = 3
DASHBOARD_PROBLEM_LIST_LIMIT = 50

# short wording for each device alert type in the devices-with-problems list
DEVICE_ISSUE_LABELS = {
    "DEVICE_OFFLINE": "Offline",
    "DEVICE_HEALTH": "Health issue",
    "DEVICE_ERROR": "Error",
    "MQTT_ERROR": "MQTT error",
    "SYSTEM_ERROR": "System error",
}


# returns the edge devices the dashboard counts
def _edge_devices(hide_inactive):
    devices = Device.objects.filter(device_type="EDGE")
    return devices.filter(active_device_q()) if hide_inactive else devices


# returns the cameras the dashboard counts
def _cameras(hide_inactive):
    cameras = Camera.objects.all()
    return cameras.filter(active_camera_q()) if hide_inactive else cameras


# returns the device and camera counts shown at the top of the dashboard
def get_dashboard_summary(hide_inactive=False):
    devices = _edge_devices(hide_inactive)
    cameras = _cameras(hide_inactive)

    return {
        "devices": devices.count(),
        "online": devices.filter(status=DeviceStatus.ONLINE).count(),
        "offline": devices.filter(status=DeviceStatus.OFFLINE).count(),
        "unknown": devices.filter(status=DeviceStatus.UNKNOWN).count(),
        "cameras": cameras.count(),
        "cameras_online": cameras.filter(status=CameraStatus.ONLINE).count(),
        "cameras_offline": cameras.filter(status=CameraStatus.OFFLINE).count(),
    }


# returns the names of the components of a device that are not healthy
def _unhealthy_components(device):
    component_statuses = device.component_statuses if isinstance(device.component_statuses, dict) else {}
    unhealthy = []

    for name, component in component_statuses.items():
        if not isinstance(component, dict):
            continue
        if not is_component_healthy(str(component.get("status", "")).lower()):
            unhealthy.append(name)

    return unhealthy


# returns the plain-english list of what is wrong with a device
def _device_issues(device, unhealthy_components):
    issues = []

    if device.status == DeviceStatus.OFFLINE:
        issues.append("Device offline")
    elif device.status == DeviceStatus.UNKNOWN:
        issues.append("Status unknown")

    if unhealthy_components:
        issues.append("Unhealthy component(s): " + ", ".join(unhealthy_components))

    for alert in device.active_alerts_prefetched:
        issues.append(DEVICE_ISSUE_LABELS.get(alert.alert_type, "Error"))

    return issues


# returns the devices that are offline, unknown, have an unhealthy component or an error alert
def get_devices_with_problems(limit=10, hide_inactive=False):
    visible_error_alerts = DeviceAlert.objects.filter(
        active=True, alert_type__in=DEVICE_ERROR_ALERT_TYPES
    ).exclude(stale_error_alert_q())

    devices = (
        _edge_devices(hide_inactive)
        .select_related("location")
        .prefetch_related(
            Prefetch("alerts", queryset=visible_error_alerts, to_attr="active_alerts_prefetched")
        )
        .annotate(
            active_alert_count=Count(
                "alerts",
                filter=Q(alerts__active=True, alerts__alert_type__in=DEVICE_ERROR_ALERT_TYPES)
                & ~stale_error_alert_q("alerts__"),
                distinct=True,
            )
        )
    )

    result = []

    for device in devices:
        unhealthy = _unhealthy_components(device)
        has_status_problem = device.status in (DeviceStatus.OFFLINE, DeviceStatus.UNKNOWN)

        if not (has_status_problem or unhealthy or device.active_alert_count > 0):
            continue

        result.append({
            "id": device.id,
            "name": device.name,
            "status": device.status,
            "location_id": device.location.id if device.location else None,
            "location_name": device.location.name if device.location else None,
            "issues": _device_issues(device, unhealthy),
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        })

    # offline first, then unknown, then the rest, most issues first
    status_priority = {DeviceStatus.OFFLINE: 0, DeviceStatus.UNKNOWN: 1}
    result.sort(key=lambda item: (status_priority.get(item["status"], 2), -len(item["issues"]), item["name"]))
    return result[:limit]


# returns the locations with offline or unknown devices, offline cameras or active error alerts
def get_locations_with_problems(limit=10, hide_inactive=False):
    device_scope = active_device_q("devices__") if hide_inactive else Q()
    camera_scope = active_camera_q("devices__cameras__") if hide_inactive else Q()

    locations = Location.objects.all()
    if hide_inactive:
        locations = locations.filter(active_location_q())

    locations = (
        locations.annotate(
            offline_devices=Count(
                "devices",
                filter=device_scope & Q(devices__status=DeviceStatus.OFFLINE),
                distinct=True,
            ),
            unknown_devices=Count(
                "devices",
                filter=device_scope & Q(devices__status=DeviceStatus.UNKNOWN),
                distinct=True,
            ),
            active_device_alerts=Count(
                "devices__alerts",
                filter=device_scope
                & Q(devices__alerts__active=True, devices__alerts__alert_type__in=DEVICE_ERROR_ALERT_TYPES)
                & ~stale_error_alert_q("devices__alerts__"),
                distinct=True,
            ),
            offline_cameras=Count(
                "devices__cameras",
                filter=camera_scope & Q(devices__cameras__status=CameraStatus.OFFLINE),
                distinct=True,
            ),
            active_camera_alerts=Count(
                "devices__cameras__alerts",
                filter=camera_scope
                & Q(
                    devices__cameras__alerts__active=True,
                    devices__cameras__alerts__alert_type__in=CAMERA_ERROR_ALERT_TYPES,
                )
                & ~stale_error_alert_q("devices__cameras__alerts__"),
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

    result = [_location_row(location) for location in locations[:limit]]
    result.sort(key=lambda row: (row["status"] != "OFFLINE", -row["problem_count"], row["name"]))
    return result[:limit]


# builds one row of the locations-with-problems list from an annotated location
def _location_row(location):
    if location.offline_devices > 0:
        status = "OFFLINE"
    elif location.unknown_devices > 0:
        status = "UNKNOWN"
    else:
        status = "WARNING"

    issue_counts = [
        (location.offline_devices, "device(s) offline"),
        (location.unknown_devices, "device(s) with unknown status"),
        (location.offline_cameras, "camera(s) offline"),
        (location.active_device_alerts, "active device alert(s)"),
        (location.active_camera_alerts, "active camera alert(s)"),
    ]

    return {
        "id": location.id,
        "name": location.name,
        "status": status,
        "offline_devices": location.offline_devices,
        "unknown_devices": location.unknown_devices,
        "active_device_alerts": location.active_device_alerts,
        "offline_cameras": location.offline_cameras,
        "active_camera_alerts": location.active_camera_alerts,
        "problem_count": sum(count for count, _ in issue_counts),
        "issues": [f"{count} {label}" for count, label in issue_counts if count > 0],
    }


# returns everything the dashboard page shows in one payload
def get_dashboard_data(hide_inactive=False):
    return {
        "summary": get_dashboard_summary(hide_inactive),
        "alert_counts": get_alert_counts(hide_inactive),
        "recent_problems": get_problem_alerts(limit=10, hide_inactive=hide_inactive),
        "recent_offline_alerts": get_problem_alerts(
            limit=DASHBOARD_PREVIEW_ROWS, category="offline", hide_inactive=hide_inactive
        ),
        "recent_error_alerts": get_problem_alerts(
            limit=DASHBOARD_PREVIEW_ROWS, category="error", hide_inactive=hide_inactive
        ),
        "devices_with_problems": get_devices_with_problems(
            limit=DASHBOARD_PROBLEM_LIST_LIMIT, hide_inactive=hide_inactive
        ),
        "locations_with_problems": get_locations_with_problems(
            limit=DASHBOARD_PROBLEM_LIST_LIMIT, hide_inactive=hide_inactive
        ),
        "recent_detections": get_camera_detections(
            limit=DASHBOARD_PREVIEW_ROWS, hide_inactive=hide_inactive
        ),
    }

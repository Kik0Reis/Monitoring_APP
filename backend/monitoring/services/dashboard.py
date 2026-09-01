"""
Monitoring dashboard aggregation service.

This is the single source of truth for the data shown on the frontend
dashboard. Previously this logic was duplicated (once here, once inline
inside monitoring/views.py::DashboardView) and the two implementations had
drifted apart, which is why the dashboard behaved inconsistently. The view
now just calls get_dashboard_data() below.
"""

from django.db.models import Count, Q

from cameras.models import Camera, CameraStatus
from devices.models import Device, DeviceStatus
from locations.models import Location
from monitoring.models import CameraAlert, CameraAlertType, DeviceAlert


def get_dashboard_summary():
    """
    Return the current monitoring summary.
    """

    devices = Device.objects.filter(active=True, device_type="EDGE")

    return {
        "devices": devices.count(),
        "online": devices.filter(status=DeviceStatus.ONLINE).count(),
        "offline": devices.filter(status=DeviceStatus.OFFLINE).count(),
        "unknown": devices.filter(status=DeviceStatus.UNKNOWN).count(),
        "cameras": Camera.objects.filter(active=True).count(),
    }


# Problems (device/camera health & connectivity issues)
#
# "Problem" alerts have an active/resolved lifecycle: the backend reuses
# the same alert row while a device stays offline (see create_offline_alert
# / create_health_alert), so filtering to active_only=True naturally shows
# exactly one row per device/camera that currently needs attention. With
# active_only=False you get the full history, including old, resolved
# alerts from devices that have flapped online/offline repeatedly.


def get_problem_alerts(limit=10, active_only=True):
    """
    Return device/camera health & connectivity problems, newest first.

    Includes: DeviceAlert (all types) and CameraAlert of type
    CAMERA_ERROR. Does NOT include CameraAlert of type CAMERA_ALERT
    (those are real-world detections, see get_camera_detections below).
    """

    device_alerts = DeviceAlert.objects.select_related("device", "device__location")

    camera_error_alerts = CameraAlert.objects.filter(
        alert_type=CameraAlertType.CAMERA_ERROR
    ).select_related(
        "camera",
        "camera__device",
        "camera__device__location",
    )

    if active_only:
        device_alerts = device_alerts.filter(active=True)
        camera_error_alerts = camera_error_alerts.filter(active=True)

    device_alerts = device_alerts.order_by("-created_at")[:limit]
    camera_error_alerts = camera_error_alerts.order_by("-created_at")[:limit]

    alerts = _serialize_device_alerts(device_alerts)
    alerts += _serialize_camera_alerts(camera_error_alerts)

    alerts.sort(key=lambda alert: alert["created_at"], reverse=True)
    alerts = alerts[:limit]

    for alert in alerts:
        alert["created_at"] = alert["created_at"].isoformat()

    return alerts


# Detections (real events reported by a camera over MQTT, e.g. smoke,
# person, or other AI-detected events)
#
# These are a chronological event log, not a "currently broken" list, so
# there's no active/resolved filtering here — every detection is shown.


def get_camera_detections(limit=50):
    camera_alerts = (
        CameraAlert.objects.filter(alert_type=CameraAlertType.CAMERA_ALERT)
        .select_related(
            "camera",
            "camera__device",
            "camera__device__location",
        )
        .order_by("-created_at")[:limit]
    )

    alerts = _serialize_camera_alerts(camera_alerts)

    for alert in alerts:
        alert["created_at"] = alert["created_at"].isoformat()

    return alerts


def _serialize_device_alerts(device_alerts):
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
    alert_type_labels = {
        "CAMERA_ALERT": "Camera",
        "CAMERA_ERROR": "Camera Error",
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


# Devices with problems
#
# Individual, device-level view of "what is currently broken" so the
# frontend dashboard can link straight to the offending device.


def _device_has_component_problem(device):
    component_statuses = (
        device.component_statuses if isinstance(device.component_statuses, dict) else {}
    )

    unhealthy = []

    for component_name, component in component_statuses.items():
        if not isinstance(component, dict):
            continue

        status = str(component.get("status", "")).lower()

        if status not in {"up", "online", "healthy"}:
            unhealthy.append(component_name)

    return unhealthy


def get_devices_with_problems(limit=10):
    """
    Return individual devices that currently need attention, e.g. because
    they are OFFLINE/UNKNOWN, have an unhealthy internal component, or have
    an active alert. Used to power a "click a broken device -> go straight
    to it" panel on the dashboard.
    """

    devices = (
        Device.objects.filter(active=True, device_type="EDGE")
        .select_related("location")
        .annotate(
            active_alert_count=Count(
                "alerts",
                filter=Q(alerts__active=True),
                distinct=True,
            ),
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

        if device.active_alert_count > 0:
            issues.append(f"{device.active_alert_count} active alert(s)")

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

    # Offline devices first, then unknown, then everything else.
    status_priority = {
        DeviceStatus.OFFLINE: 0,
        DeviceStatus.UNKNOWN: 1,
    }

    result.sort(
        key=lambda item: (
            status_priority.get(item["status"], 2),
            -len(item["issues"]),
            item["name"],
        )
    )

    return result[:limit]


def get_locations_with_problems(limit=10):
    """
    Return locations that currently have monitoring problems.

    A location is considered problematic when it has:

    - an offline or unknown device
    - an active device alert
    - an offline or unknown camera
    - an active camera alert
    """

    locations = (
        Location.objects.annotate(
            offline_devices=Count(
                "devices",
                filter=Q(
                    devices__active=True,
                    devices__status=DeviceStatus.OFFLINE,
                ),
                distinct=True,
            ),
            unknown_devices=Count(
                "devices",
                filter=Q(
                    devices__active=True,
                    devices__status=DeviceStatus.UNKNOWN,
                ),
                distinct=True,
            ),
            active_device_alerts=Count(
                "devices__alerts",
                filter=Q(
                    devices__active=True,
                    devices__alerts__active=True,
                ),
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
                    devices__cameras__active=True,
                    devices__cameras__alerts__active=True,
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
    """
    Return all data required by the monitoring dashboard.
    """

    return {
        "summary": get_dashboard_summary(),
        # Active-only, deduped problems: the backend reuses a single alert
        # row while something stays broken, so this naturally shows one
        # entry per currently-broken device/camera instead of repeating a
        # flapping device's entire history.
        "recent_problems": get_problem_alerts(limit=10, active_only=True),
        "devices_with_problems": get_devices_with_problems(),
        "locations_with_problems": get_locations_with_problems(),
    }

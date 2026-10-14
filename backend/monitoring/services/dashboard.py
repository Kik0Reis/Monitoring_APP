"""Builds all the data the frontend dashboard needs. Single source of truth --
views.py just calls get_dashboard_data()."""

from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from cameras.models import Camera, CameraStatus
from devices.models import Device, DeviceStatus
from locations.models import Location
from monitoring.models import AlertType, CameraAlert, CameraAlertType, DeviceAlert
from monitoring.services.device_health import is_component_healthy


def get_dashboard_summary():
    """Return the top-line device/camera counts shown at the top of the dashboard."""

    devices = Device.objects.filter(active=True, device_type="EDGE")
    cameras = Camera.objects.filter(active=True)

    return {
        "devices": devices.count(),
        "online": devices.filter(status=DeviceStatus.ONLINE).count(),
        "offline": devices.filter(status=DeviceStatus.OFFLINE).count(),
        "unknown": devices.filter(status=DeviceStatus.UNKNOWN).count(),
        "cameras": cameras.count(),
        "cameras_online": cameras.filter(status=CameraStatus.ONLINE).count(),
        "cameras_offline": cameras.filter(status=CameraStatus.OFFLINE).count(),
    }


# DEVICE_OFFLINE/CAMERA_OFFLINE describe a device/camera that's currently
# unreachable -- a real, ongoing state, so they stay visible for as long as
# they're active, however long that is.
#
# DEVICE_HEALTH is the periodic component healthcheck (detectorapi,
# detector, idmr, ... reporting "down"/unhealthy) -- still a *status*,
# not a one-off reported problem.
#
# Everything else (DEVICE_ERROR, MQTT_ERROR, SYSTEM_ERROR, CAMERA_ERROR) is
# a free-form message the Edge/camera actually sent over MQTT (e.g. "low
# threshold", a licensing problem, a crash) -- these are what the frontend
# splits into their own "Errors" section, separate from both offline and
# healthcheck alerts.
_OFFLINE_ALERT_TYPES = {AlertType.DEVICE_OFFLINE, CameraAlertType.CAMERA_OFFLINE}
_HEALTH_ALERT_TYPES = {AlertType.DEVICE_HEALTH}
_ERROR_ALERT_TYPES = {
    AlertType.DEVICE_ERROR,
    AlertType.MQTT_ERROR,
    AlertType.SYSTEM_ERROR,
    CameraAlertType.CAMERA_ERROR,
}


def _alert_category(alert_type):
    if alert_type in _OFFLINE_ALERT_TYPES:
        return "offline"
    if alert_type in _HEALTH_ALERT_TYPES:
        return "health"
    return "error"


def _error_alert_visible_cutoff():
    return timezone.now() - timezone.timedelta(hours=settings.ALERT_VISIBLE_HOURS)


def _stale_error_alert_q(prefix=""):
    """Q object matching an "error"-category alert (see _alert_category)
    that's older than settings.ALERT_VISIBLE_HOURS -- stale enough that it
    should stop counting as a current problem even though active=True is
    still set (it only flips to active=False when resolved/re-reported,
    see device_health.py/camera_monitor.py).

    This is the ONE place that rule is expressed. Every place that decides
    whether an error alert currently counts as "a problem" --
    get_problem_alerts, get_devices_with_problems,
    get_locations_with_problems, the Device/Camera detail serializers,
    and the monitor tree (monitoring/services/tree.py) -- excludes
    against this same Q, so a stale error can't keep showing up as a
    problem in some places just because one particular query forgot to
    apply the cutoff.

    `prefix` lets this reach through a relation with .exclude(), e.g.
    _stale_error_alert_q("alerts__") or
    _stale_error_alert_q("devices__cameras__alerts__"). Combine with other
    filters via `&`/`~` as needed; it says nothing about `active` itself.
    """

    error_types = [
        AlertType.DEVICE_ERROR,
        AlertType.MQTT_ERROR,
        AlertType.SYSTEM_ERROR,
        CameraAlertType.CAMERA_ERROR,
    ]

    return Q(**{f"{prefix}alert_type__in": error_types}) & Q(
        **{f"{prefix}created_at__lt": _error_alert_visible_cutoff()}
    )


def _problem_querysets(active_only=True, category=None):
    """The (DeviceAlert, CameraAlert) querysets behind get_problem_alerts().

    Shared with get_alert_counts() so the dashboard counters can never
    disagree with the list you get when you open them.
    """


    device_alerts = DeviceAlert.objects.select_related("device", "device__location")

    camera_problem_alerts = CameraAlert.objects.filter(
        alert_type__in=[CameraAlertType.CAMERA_ERROR, CameraAlertType.CAMERA_OFFLINE]
    ).select_related("camera", "camera__device", "camera__device__location")

    if active_only:
        device_alerts = device_alerts.filter(active=True)
        camera_problem_alerts = camera_problem_alerts.filter(active=True)

        # The "hide after N hours" window only applies to the live view;
        # history (active_only=False) shows everything still stored.
        # Applied unconditionally here (not just when category="error")
        # so every caller gets a consistent view, including the merged
        # category=None list.
        device_alerts = device_alerts.exclude(_stale_error_alert_q())
        camera_problem_alerts = camera_problem_alerts.exclude(_stale_error_alert_q())

    if category == "offline":
        device_alerts = device_alerts.filter(alert_type=AlertType.DEVICE_OFFLINE)
        camera_problem_alerts = camera_problem_alerts.filter(
            alert_type=CameraAlertType.CAMERA_OFFLINE
        )
    elif category == "health":
        device_alerts = device_alerts.filter(alert_type=AlertType.DEVICE_HEALTH)
        camera_problem_alerts = camera_problem_alerts.none()
    elif category == "error":
        device_alerts = device_alerts.filter(
            alert_type__in=[
                AlertType.DEVICE_ERROR,
                AlertType.MQTT_ERROR,
                AlertType.SYSTEM_ERROR,
            ]
        )
        camera_problem_alerts = camera_problem_alerts.filter(
            alert_type=CameraAlertType.CAMERA_ERROR
        )

    return device_alerts, camera_problem_alerts


def get_problem_alerts(limit=10, active_only=True, category=None):
    """Device/camera health & connectivity problems, newest first.

    DeviceAlert (all types) + CameraAlert of type CAMERA_ERROR/CAMERA_OFFLINE.
    Not CAMERA_ALERT, those are real detections (see get_camera_detections).
    active_only=True naturally dedupes to one row per broken thing, since
    the alert row is reused while it stays broken rather than re-created.

    category, when given, is one of:
      - "offline": device/camera currently unreachable.
      - "health":  a component healthcheck (DEVICE_HEALTH) reporting an
        unhealthy component.
      - "error":   a free-form message actually sent over MQTT (DEVICE_ERROR,
        MQTT_ERROR, SYSTEM_ERROR, CAMERA_ERROR) -- e.g. "low threshold".

    "error" alerts also disappear on their own after
    settings.ALERT_VISIBLE_HOURS, even if still active/being re-reported --
    "offline"/"health" alerts have no such cutoff, since they represent a
    real, ongoing state for as long as they stay active.
    """
    device_alerts, camera_problem_alerts = _problem_querysets(active_only, category)

    device_alerts = device_alerts.order_by("-created_at")[:limit]
    camera_problem_alerts = camera_problem_alerts.order_by("-created_at")[:limit]

    alerts = _serialize_device_alerts(device_alerts)
    alerts += _serialize_camera_alerts(camera_problem_alerts)

    alerts.sort(key=lambda alert: alert["created_at"], reverse=True)
    alerts = alerts[:limit]

    for alert in alerts:
        alert["created_at"] = alert["created_at"].isoformat()

    return alerts


def _detections_queryset():
    cutoff = timezone.now() - timezone.timedelta(hours=settings.DETECTION_VISIBLE_HOURS)

    return CameraAlert.objects.filter(
        alert_type=CameraAlertType.CAMERA_ALERT, created_at__gte=cutoff, active=True
    ).select_related("camera", "camera__device", "camera__device__location")


def get_alert_counts():
    """True totals behind the dashboard's clickable counters.

    The dashboard payload itself only carries a short preview of each list,
    so the counters need their own cheap COUNT queries (same filters as the
    lists, see _problem_querysets/_detections_queryset).
    """

    counts = {}

    for category in ("offline", "error"):
        device_qs, camera_qs = _problem_querysets(active_only=True, category=category)
        counts[category] = device_qs.count() + camera_qs.count()

    counts["detections"] = _detections_queryset().count()

    return counts


def get_camera_detections(limit=50):
    """Most recent real-world detections (CAMERA_ALERT), newest first.

    Chronological log, so no active/resolved filtering by default -- except
    a detection that's been manually marked resolved (active=False, see
    monitoring.views.CameraAlertResolveView) drops out of this list. If the
    same detection is re-reported on MQTT it gets a brand new row, so it
    naturally reappears.

    Restricted to the last settings.DETECTION_VISIBLE_HOURS regardless of
    `limit`, so detections disappear from the feed on their own after about
    a day -- separate from settings.DETECTION_RETENTION_DAYS, which is when
    the row is physically deleted (see
    monitoring/services/retention.py:delete_old_detections).
    """

    camera_alerts = _detections_queryset().order_by("-created_at")[:limit]

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
                "category": _alert_category(alert.alert_type),
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
        payload = alert.raw_payload if isinstance(alert.raw_payload, dict) else {}

        alerts.append(
            {
                "id": f"camera-{alert.id}",
                "type": alert_type_labels.get(alert.alert_type, "Camera"),
                "alert_type": alert.alert_type,
                "category": _alert_category(alert.alert_type),
                "severity": alert.severity,
                "device_id": device.id if device else None,
                "device_name": device.name if device else None,
                "location_id": location.id if location else None,
                "location_name": location.name if location else None,
                "camera_id": camera.id,
                "camera_name": camera.name,
                # what the camera detected / which action fired, from the MQTT
                # payload (only set for real detections)
                "detected": payload.get("class_label"),
                "action_code": payload.get("action_code"),
                "confidence": payload.get("confidence"),
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
    """Devices needing attention: OFFLINE/UNKNOWN, unhealthy component, or active error alert.

    "active alert" here specifically means an "error"-category alert
    (DEVICE_ERROR/MQTT_ERROR/SYSTEM_ERROR, see _alert_category) -- not
    DEVICE_OFFLINE (already covered by the status check above, so
    counting it again here would both double-count it and print a
    redundant "Offline" issue alongside "Device offline") and not
    DEVICE_HEALTH (already reflected via unhealthy_components above).
    """

    error_alert_types = [
        AlertType.DEVICE_ERROR,
        AlertType.MQTT_ERROR,
        AlertType.SYSTEM_ERROR,
    ]

    devices = (
        Device.objects.filter(active=True, device_type="EDGE")
        .select_related("location")
        .prefetch_related(
            Prefetch(
                "alerts",
                queryset=DeviceAlert.objects.filter(
                    active=True, alert_type__in=error_alert_types
                ).exclude(_stale_error_alert_q()),
                to_attr="active_alerts_prefetched",
            )
        )
        .annotate(
            active_alert_count=Count(
                "alerts",
                filter=Q(alerts__active=True, alerts__alert_type__in=error_alert_types)
                & ~_stale_error_alert_q("alerts__"),
                distinct=True,
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
    """Locations with an offline/unknown device or camera, or an active error alert.

    Each result gets a short "issues" list (e.g. "2 device(s) offline")
    instead of just a raw count.

    active_device_alerts/active_camera_alerts count only "error"-category
    alerts (DEVICE_ERROR/MQTT_ERROR/SYSTEM_ERROR, CAMERA_ERROR -- see
    _alert_category), the same definition used everywhere else (dashboard
    Errors panel, monitor tree, alerts page). In particular this means:
      - DEVICE_OFFLINE/CAMERA_OFFLINE alerts are excluded -- offline_devices/
        offline_cameras (based on the device/camera's own status) already
        cover that, counting the alert too would double it up.
      - CAMERA_ALERT (real detections) are excluded. Detections are
        events, not problems, and -- unlike offline/error alerts --
        they never flip to active=False on their own when they age out of
        view (see monitoring/services/dashboard.py:_detections_queryset),
        so leaving them uncounted here was letting an old, long-gone
        detection keep inflating "N active camera alert(s)" on the
        dashboard indefinitely.
    """

    device_error_types = [
        AlertType.DEVICE_ERROR,
        AlertType.MQTT_ERROR,
        AlertType.SYSTEM_ERROR,
    ]

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
                filter=Q(
                    devices__active=True,
                    devices__alerts__active=True,
                    devices__alerts__alert_type__in=device_error_types,
                )
                & ~_stale_error_alert_q("devices__alerts__"),
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
                    devices__cameras__alerts__alert_type=CameraAlertType.CAMERA_ERROR,
                )
                & ~_stale_error_alert_q("devices__cameras__alerts__"),
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


# How many rows of each list ride along in the dashboard payload. The
# dashboard only previews a few of each; "View all" fetches the full list
# from /api/problems/ and /api/detections/, and the counters come from
# alert_counts, so this can stay small.
DASHBOARD_PREVIEW_ROWS = 3

# The devices/locations panels have no separate endpoint, so the "View all"
# pop-up reads them straight from this payload -- hence the higher cap.
DASHBOARD_PROBLEM_LIST_LIMIT = 50


def get_dashboard_data():
    """Everything the monitoring dashboard needs, in one call.

    recent_offline_alerts / recent_error_alerts / recent_detections are only
    a short preview (DASHBOARD_PREVIEW_ROWS); alert_counts has the real
    totals for the clickable counters:
      - offline: device/camera currently unreachable.
      - error:   free-form MQTT messages (e.g. "low threshold").
      - detections: real camera events.

    DEVICE_HEALTH alerts (category="health") are deliberately left out --
    they're what the monitoring services use internally to compute a
    device's online/offline status (see device_health.py), not a separate
    user-facing problem.

    recent_problems is kept for backwards compatibility (merged, all
    categories).
    """

    return {
        "summary": get_dashboard_summary(),
        "alert_counts": get_alert_counts(),
        "recent_problems": get_problem_alerts(limit=10, active_only=True),
        "recent_offline_alerts": get_problem_alerts(
            limit=DASHBOARD_PREVIEW_ROWS, active_only=True, category="offline"
        ),
        "recent_error_alerts": get_problem_alerts(
            limit=DASHBOARD_PREVIEW_ROWS, active_only=True, category="error"
        ),
        "devices_with_problems": get_devices_with_problems(
            limit=DASHBOARD_PROBLEM_LIST_LIMIT
        ),
        "locations_with_problems": get_locations_with_problems(
            limit=DASHBOARD_PROBLEM_LIST_LIMIT
        ),
        "recent_detections": get_camera_detections(limit=DASHBOARD_PREVIEW_ROWS),
    }

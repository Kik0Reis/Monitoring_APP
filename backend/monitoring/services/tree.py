"""Builds the nested Country -> Customer -> Location -> Device -> Camera
tree for the "Monitor > Views" page (see monitoring/views.py:MonitorTreeView).

Every node carries three independent indicators, same meaning at every
level of the tree:

  - system_check: "red" if this node, or ANY descendant, is OFFLINE.
    "green" otherwise. This is a rollup -- a location can show red even
    though the location itself has no "status" of its own, because one of
    its devices or cameras is offline. A device/camera can show red on
    its own status even with no children at all.
  - has_alerts: True if this node, or any descendant, has an active
    "error" category alert (see monitoring/services/dashboard.py's
    _alert_category for what counts as "error" vs "offline"/"health" --
    same categories, reused here so the tree and the dashboard never
    disagree about what an "error" is).
  - detections_count: how many recent detections (same
    DETECTION_VISIBLE_HOURS window as the dashboard) sit under this node.

Every node also carries "active" (the record's own active flag; countries
have none, so they are always True).

get_monitor_tree(active_only=...) controls how inactive records count:

  - active_only=False (default): everything is in the tree and inactive
    devices/cameras count towards the rollup like any other, so an inactive
    node that is offline turns its parents red.
  - active_only=True: inactive customers/locations/devices/cameras are left
    out entirely (together with everything under them), so they can't
    affect any colour or count. Parents are red only if an *active*
    device/camera below them is offline.

This intentionally loads the whole tree in a handful of queries rather
than one query per node -- fine at the scale this app runs at (see the
Future Enhancements section of the project plan for when that stops being
true), and it means system_check/has_alerts can never drift out of sync
between parent and child the way per-node lazy loading could.
"""

from countries.models import Country
from devices.models import DeviceStatus
from cameras.models import CameraStatus
from monitoring.models import AlertType, CameraAlert, CameraAlertType, DeviceAlert
from monitoring.services.dashboard import _detections_queryset, _stale_error_alert_q


def get_monitor_tree(active_only=False):
    def keep(record):
        return record.active or not active_only

    countries = (
        Country.objects.all()
        .prefetch_related(
            "customers",
            "customers__locations",
            "customers__locations__devices",
            "customers__locations__devices__cameras",
        )
        .order_by("name")
    )

    # One query each for "which devices/cameras currently have an active,
    # still-visible error alert", used to set has_alerts at the leaf level
    # -- everything above a device/camera just ORs its children together.
    # .exclude(_stale_error_alert_q()) is the same "hide after
    # settings.ALERT_VISIBLE_HOURS" rule the dashboard/alerts page use, so
    # a stale error alert can't still light up the tree amber after it's
    # already disappeared everywhere else (see dashboard.py:
    # _stale_error_alert_q's docstring).
    device_error_ids = set(
        DeviceAlert.objects.filter(
            active=True,
            alert_type__in=[AlertType.DEVICE_ERROR, AlertType.MQTT_ERROR, AlertType.SYSTEM_ERROR],
        )
        .exclude(_stale_error_alert_q())
        .values_list("device_id", flat=True)
    )
    camera_error_ids = set(
        CameraAlert.objects.filter(active=True, alert_type=CameraAlertType.CAMERA_ERROR)
        .exclude(_stale_error_alert_q())
        .values_list("camera_id", flat=True)
    )

    # Detections per camera, same visibility window as the dashboard/alerts
    # page (settings.DETECTION_VISIBLE_HOURS).
    detections_by_camera = {}
    for camera_id in _detections_queryset().values_list("camera_id", flat=True):
        detections_by_camera[camera_id] = detections_by_camera.get(camera_id, 0) + 1

    def camera_node(camera):
        red = camera.status == CameraStatus.OFFLINE
        return {
            "type": "camera",
            "id": camera.id,
            "name": camera.name,
            "status": camera.status.lower(),
            "active": camera.active,
            "pending_review": camera.pending_review,
            "system_check": "red" if red else "green",
            "has_alerts": camera.id in camera_error_ids,
            "detections_count": detections_by_camera.get(camera.id, 0),
            "children": [],
        }

    def device_node(device):
        cameras = [camera_node(c) for c in device.cameras.all() if keep(c)]
        own_red = device.status == DeviceStatus.OFFLINE
        return {
            "type": "device",
            "id": device.id,
            "name": device.name,
            "status": device.status.lower(),
            "active": device.active,
            "pending_review": device.pending_review,
            "system_check": "red"
            if own_red or any(c["system_check"] == "red" for c in cameras)
            else "green",
            "has_alerts": device.id in device_error_ids or any(c["has_alerts"] for c in cameras),
            "detections_count": sum(c["detections_count"] for c in cameras),
            "children": cameras,
        }

    def location_node(location):
        devices = [device_node(d) for d in location.devices.all() if keep(d)]
        return {
            "type": "location",
            "id": location.id,
            "name": location.name,
            "active": location.active,
            "pending_review": location.pending_review,
            "system_check": "red" if any(d["system_check"] == "red" for d in devices) else "green",
            "has_alerts": any(d["has_alerts"] for d in devices),
            "detections_count": sum(d["detections_count"] for d in devices),
            "children": devices,
        }

    def customer_node(customer):
        locations = [location_node(l) for l in customer.locations.all() if keep(l)]
        return {
            "type": "customer",
            "id": customer.id,
            "name": customer.name,
            "active": customer.active,
            "pending_review": customer.pending_review,
            "system_check": "red" if any(l["system_check"] == "red" for l in locations) else "green",
            "has_alerts": any(l["has_alerts"] for l in locations),
            "detections_count": sum(l["detections_count"] for l in locations),
            "children": locations,
        }

    def country_node(country):
        customers = [customer_node(c) for c in country.customers.all() if keep(c)]
        return {
            "type": "country",
            "id": country.id,
            "name": country.name,
            "active": True,
            "pending_review": country.pending_review,
            "system_check": "red" if any(c["system_check"] == "red" for c in customers) else "green",
            "has_alerts": any(c["has_alerts"] for c in customers),
            "detections_count": sum(c["detections_count"] for c in customers),
            "children": customers,
        }

    return [country_node(country) for country in countries]

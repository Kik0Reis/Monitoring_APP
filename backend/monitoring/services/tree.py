from cameras.models import CameraStatus
from core.alert_rules import CAMERA_ERROR_ALERT_TYPES, DEVICE_ERROR_ALERT_TYPES
from countries.models import Country
from devices.models import DeviceStatus
from monitoring.models import CameraAlert, DeviceAlert
from monitoring.services.alert_queries import detections_queryset, stale_error_alert_q


# builds one tree node and rolls the indicators of its children up into it
def _node(node_type, record, children, own_offline=False, own_alert=False, own_detections=0, status=None):
    node = {
        "type": node_type,
        "id": record.id,
        "name": record.name,
        "active": getattr(record, "active", True),
        "pending_review": record.pending_review,
        "system_check": "red" if own_offline or any(c["system_check"] == "red" for c in children) else "green",
        "has_alerts": own_alert or any(c["has_alerts"] for c in children),
        "detections_count": own_detections + sum(c["detections_count"] for c in children),
        "children": children,
    }

    if status is not None:
        node["status"] = status

    return node


# returns the ids of the devices and of the cameras that have a visible error alert
def _ids_with_error_alerts():
    device_ids = set(
        DeviceAlert.objects.filter(active=True, alert_type__in=DEVICE_ERROR_ALERT_TYPES)
        .exclude(stale_error_alert_q())
        .values_list("device_id", flat=True)
    )
    camera_ids = set(
        CameraAlert.objects.filter(active=True, alert_type__in=CAMERA_ERROR_ALERT_TYPES)
        .exclude(stale_error_alert_q())
        .values_list("camera_id", flat=True)
    )
    return device_ids, camera_ids


# returns how many visible detections each camera has, keyed by camera id
def _detections_per_camera():
    counts = {}

    for camera_id in detections_queryset().values_list("camera_id", flat=True):
        counts[camera_id] = counts.get(camera_id, 0) + 1

    return counts


# builds the Country > Customer > Location > Device > Camera tree for the Monitor page
# with hide_inactive, inactive records are left out together with everything under them,
# so they can no longer change the colour of the nodes above
def get_monitor_tree(hide_inactive=False):
    device_error_ids, camera_error_ids = _ids_with_error_alerts()
    detections_by_camera = _detections_per_camera()

    # keeps a record when it is active, or when inactive ones are being shown
    def keep(record):
        return record.active or not hide_inactive

    # builds the node of a camera
    def camera_node(camera):
        return _node(
            "camera",
            camera,
            [],
            own_offline=camera.status == CameraStatus.OFFLINE,
            own_alert=camera.id in camera_error_ids,
            own_detections=detections_by_camera.get(camera.id, 0),
            status=camera.status.lower(),
        )

    # builds the node of a device with its visible cameras
    def device_node(device):
        cameras = [camera_node(camera) for camera in device.cameras.all() if keep(camera)]
        return _node(
            "device",
            device,
            cameras,
            own_offline=device.status == DeviceStatus.OFFLINE,
            own_alert=device.id in device_error_ids,
            status=device.status.lower(),
        )

    # builds the node of a location with its visible devices
    def location_node(location):
        return _node("location", location, [device_node(d) for d in location.devices.all() if keep(d)])

    # builds the node of a customer with its visible locations
    def customer_node(customer):
        return _node("customer", customer, [location_node(l) for l in customer.locations.all() if keep(l)])

    # builds the node of a country with its visible customers
    def country_node(country):
        return _node("country", country, [customer_node(c) for c in country.customers.all() if keep(c)])

    countries = Country.objects.prefetch_related(
        "customers",
        "customers__locations",
        "customers__locations__devices",
        "customers__locations__devices__cameras",
    ).order_by("name")

    return [country_node(country) for country in countries]

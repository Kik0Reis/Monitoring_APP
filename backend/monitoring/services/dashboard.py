from django.db.models import Count, Q

from cameras.models import Camera, CameraStatus
from devices.models import Device, DeviceStatus
from locations.models import Location
from monitoring.models import (
    CameraAlert,
    DeviceAlert,
)


def get_dashboard_summary():
    """
    Return the current monitoring summary.
    """

    return {
        "devices": Device.objects.filter(
            active=True,
            device_type="EDGE",
        ).count(),

        "online": Device.objects.filter(
            active=True,
            device_type="EDGE",
            status=DeviceStatus.ONLINE,
        ).count(),

        "offline": Device.objects.filter(
            active=True,
            device_type="EDGE",
            status=DeviceStatus.OFFLINE,
        ).count(),

        "cameras": Camera.objects.filter(
            active=True,
        ).count(),
    }


def get_recent_alerts(limit=10):
    """
    Return recent device and camera alerts.

    DeviceAlert and CameraAlert are separate models, so we combine
    them in Python after fetching the latest records.
    """

    device_alerts = (
        DeviceAlert.objects
        .select_related(
            "device",
            "device__location",
        )
        .order_by("-created_at")[:limit]
    )

    camera_alerts = (
        CameraAlert.objects
        .select_related(
            "camera",
            "camera__device",
            "camera__device__location",
        )
        .order_by("-created_at")[:limit]
    )

    alerts = []

    for alert in device_alerts:
        alerts.append({
            "id": f"device-{alert.id}",
            "type": "Health"
            if alert.alert_type == "DEVICE_HEALTH"
            else "Offline"
            if alert.alert_type == "DEVICE_OFFLINE"
            else "Device",

            "alert_type": alert.alert_type,
            "severity": alert.severity,

            "device_id": alert.device.id,
            "device_name": alert.device.name,

            "location_id": alert.device.location.id,
            "location_name": alert.device.location.name,

            "camera_id": None,
            "camera_name": None,

            "message": alert.message,
            "active": alert.active,
            "created_at": alert.created_at,
        })

    for alert in camera_alerts:
        alerts.append({
            "id": f"camera-{alert.id}",
            "type": "Camera",

            "alert_type": alert.alert_type,
            "severity": alert.severity,

            "device_id": alert.camera.device.id,
            "device_name": alert.camera.device.name,

            "location_id": (
                alert.camera.device.location.id
            ),
            "location_name": (
                alert.camera.device.location.name
            ),

            "camera_id": alert.camera.id,
            "camera_name": alert.camera.name,

            "message": alert.message,
            "active": alert.active,
            "created_at": alert.created_at,
        })

    alerts.sort(
        key=lambda alert: alert["created_at"],
        reverse=True,
    )

    return alerts[:limit]


def get_problematic_locations(limit=10):
    """
    Return locations that currently have monitoring problems.

    A location is considered problematic when it has:

    - an offline device
    - an active device alert
    - an offline camera
    - an active camera alert
    """

    locations = (
        Location.objects
        .annotate(
            offline_devices=Count(
                "devices",
                filter=Q(
                    devices__active=True,
                    devices__status=DeviceStatus.OFFLINE,
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
            + location.active_device_alerts
            + location.offline_cameras
            + location.active_camera_alerts
        )

        result.append({
            "id": location.id,
            "name": location.name,
            "status": (
                "OFFLINE"
                if location.offline_devices > 0
                else "WARNING"
            ),
            "offline_devices": location.offline_devices,
            "active_device_alerts": (
                location.active_device_alerts
            ),
            "offline_cameras": location.offline_cameras,
            "active_camera_alerts": (
                location.active_camera_alerts
            ),
            "problem_count": problem_count,
        })

    return result


def get_dashboard_data():
    """
    Return all data required by the monitoring dashboard.
    """

    return {
        "summary": get_dashboard_summary(),
        "recent_alerts": get_recent_alerts(),
        "problematic_locations": (
            get_problematic_locations()
        ),
    }
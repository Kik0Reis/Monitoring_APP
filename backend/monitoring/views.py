from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView

from devices.models import Device, DeviceStatus
from cameras.models import Camera

from .models import (
    DeviceAlert,
    CameraAlert,
)


class DashboardView(APIView):
    """
    Monitoring dashboard API.

    Provides aggregated monitoring information for the frontend.

    Endpoint:

        GET /api/monitoring/dashboard/

    Returns:

        - device summary
        - camera summary
        - recent active alerts
        - locations with active problems
    """

    def get(self, request):

        # ==================================================================
        # Base querysets
        # ==================================================================

        devices = Device.objects.filter(
            active=True,
        ).select_related(
            "location",
        )

        cameras = Camera.objects.filter(
            active=True,
        ).select_related(
            "device",
            "device__location",
        )

        # ==================================================================
        # SUMMARY
        # ==================================================================

        total_devices = devices.count()

        online_devices = devices.filter(
            status=DeviceStatus.ONLINE,
        ).count()

        offline_devices = devices.filter(
            status=DeviceStatus.OFFLINE,
        ).count()

        unknown_devices = devices.filter(
            status=DeviceStatus.UNKNOWN,
        ).count()

        total_cameras = cameras.count()

        # ==================================================================
        # ACTIVE DEVICE ALERTS
        # ==================================================================

        device_alerts = (
            DeviceAlert.objects
            .filter(
                active=True,
                device__active=True,
            )
            .select_related(
                "device",
                "device__location",
            )
            .order_by("-created_at")
        )

        # ==================================================================
        # ACTIVE CAMERA ALERTS
        # ==================================================================

        camera_alerts = (
            CameraAlert.objects
            .filter(
                active=True,
                camera__active=True,
            )
            .select_related(
                "camera",
                "camera__device",
                "camera__device__location",
            )
            .order_by("-created_at")
        )

        # ==================================================================
        # RECENT ALERTS
        #
        # Combine device and camera alerts.
        # ==================================================================

        recent_alerts = []

        for alert in device_alerts[:20]:

            recent_alerts.append({
                "id": alert.id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,

                "device_id": alert.device.id,
                "device_name": alert.device.name,

                "camera_id": None,
                "camera_name": None,

                "location_id": (
                    alert.device.location.id
                    if alert.device.location
                    else None
                ),

                "location_name": (
                    alert.device.location.name
                    if alert.device.location
                    else None
                ),

                "created_at": alert.created_at,
            })

        for alert in camera_alerts[:20]:

            camera = alert.camera
            device = camera.device
            location = device.location

            recent_alerts.append({
                "id": alert.id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,

                "device_id": device.id,
                "device_name": device.name,

                "camera_id": camera.id,
                "camera_name": camera.name,

                "location_id": (
                    location.id
                    if location
                    else None
                ),

                "location_name": (
                    location.name
                    if location
                    else None
                ),

                "created_at": alert.created_at,
            })

        # Sort combined alerts by creation time.
        recent_alerts.sort(
            key=lambda alert: alert["created_at"],
            reverse=True,
        )

        # Only return the most recent 10.
        recent_alerts = recent_alerts[:10]

        # Convert datetime objects to ISO strings.
        for alert in recent_alerts:

            alert["created_at"] = (
                alert["created_at"].isoformat()
            )

        # ==================================================================
        # LOCATIONS WITH PROBLEMS
        #
        # A location has a problem when it contains:
        #
        # - an offline device
        # - an unknown device
        # - an active device alert
        # - an active camera alert
        # - an offline camera
        #
        # ==================================================================

        locations = {}

        # --------------------------------------------------------------
        # Device problems
        # --------------------------------------------------------------

        for device in devices:

            has_device_problem = (
                device.status == DeviceStatus.OFFLINE
                or device.status == DeviceStatus.UNKNOWN
            )

            has_component_problem = False

            component_statuses = (
                device.component_statuses
                if isinstance(
                    device.component_statuses,
                    dict,
                )
                else {}
            )

            for component_name, component in (
                component_statuses.items()
            ):

                if not isinstance(component, dict):
                    continue

                component_status = (
                    component.get("status")
                )

                if component_status != "up":
                    has_component_problem = True
                    break

            has_active_device_alert = (
                device.alerts
                .filter(active=True)
                .exists()
            )

            if (
                has_device_problem
                or has_component_problem
                or has_active_device_alert
            ):

                location = device.location

                if location:

                    if location.id not in locations:

                        locations[location.id] = {
                            "id": location.id,
                            "name": location.name,
                            "devices": 0,
                            "cameras": 0,
                            "problem_count": 0,
                            "status": "ONLINE",
                        }

                    locations[
                        location.id
                    ]["devices"] += 1

                    locations[
                        location.id
                    ]["problem_count"] += 1

                    if device.status == DeviceStatus.OFFLINE:

                        locations[
                            location.id
                        ]["status"] = "OFFLINE"

                    elif (
                        device.status
                        == DeviceStatus.UNKNOWN
                        and locations[
                            location.id
                        ]["status"] == "ONLINE"
                    ):

                        locations[
                            location.id
                        ]["status"] = "UNKNOWN"

        # --------------------------------------------------------------
        # Camera problems
        # --------------------------------------------------------------

        for camera in cameras:

            has_camera_problem = (
                camera.status != "ONLINE"
            )

            has_active_camera_alert = (
                camera.alerts
                .filter(active=True)
                .exists()
            )

            if (
                has_camera_problem
                or has_active_camera_alert
            ):

                device = camera.device
                location = device.location

                if not location:
                    continue

                if location.id not in locations:

                    locations[location.id] = {
                        "id": location.id,
                        "name": location.name,
                        "devices": 0,
                        "cameras": 0,
                        "problem_count": 0,
                        "status": "ONLINE",
                    }

                locations[
                    location.id
                ]["cameras"] += 1

                locations[
                    location.id
                ]["problem_count"] += 1

                if camera.status == "OFFLINE":

                    locations[
                        location.id
                    ]["status"] = "OFFLINE"

                elif (
                    camera.status == "UNKNOWN"
                    and locations[
                        location.id
                    ]["status"] == "ONLINE"
                ):

                    locations[
                        location.id
                    ]["status"] = "UNKNOWN"

        # ==================================================================
        # Make location list
        # ==================================================================

        locations_with_problems = list(
            locations.values()
        )

        locations_with_problems.sort(
            key=lambda location: (
                location["status"] != "OFFLINE",
                -location["problem_count"],
                location["name"],
            )
        )

        # ==================================================================
        # RETURN RESPONSE
        # ==================================================================

        return Response({

            "summary": {
                "devices": total_devices,
                "online": online_devices,
                "offline": offline_devices,
                "unknown": unknown_devices,
                "cameras": total_cameras,
            },

            "recent_alerts": recent_alerts,

            "locations_with_problems": (
                locations_with_problems
            ),
        })
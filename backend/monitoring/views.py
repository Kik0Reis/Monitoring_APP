from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.models import CameraAlert, DeviceAlert
from monitoring.services.dashboard import (
    get_camera_detections,
    get_dashboard_data,
    get_problem_alerts,
)


class DashboardView(APIView):
    """
    Monitoring dashboard API.

    Provides aggregated monitoring information for the frontend.

    Endpoint:

        GET /api/dashboard/

    Returns:

        - device summary
        - recent (active) problems
        - devices with active problems (click through to the device)
        - locations with active problems (click through to the location)

    All aggregation logic lives in monitoring.services.dashboard so there
    is exactly one implementation to keep in sync with the frontend.
    """

    def get(self, request):
        return Response(get_dashboard_data())


def _clamp_limit(request, default, maximum):
    limit = request.query_params.get("limit", default)

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = default

    return max(1, min(limit, maximum))


class ProblemsView(APIView):
    """
    Device/camera health & connectivity problems (offline devices,
    unhealthy components, MQTT/system errors, camera errors).

    Endpoint:

        GET /api/problems/?limit=100&active_only=true&category=error

    active_only defaults to true: the backend reuses a single alert row
    while something stays broken, so this naturally shows one row per
    currently-broken device/camera. Pass active_only=false to also see
    resolved history (useful for a device that has flapped online/offline
    many times).

    category optionally filters to "offline" (device/camera currently
    unreachable), "health" (component healthcheck), or "error" (a
    free-form message actually sent over MQTT, e.g. "low threshold") --
    this is what lets the frontend show these as separate sections
    instead of one mixed list.
    """

    def get(self, request):
        limit = _clamp_limit(request, default=100, maximum=500)

        active_only = request.query_params.get("active_only", "true")
        active_only = str(active_only).lower() not in ("false", "0", "no")

        category = request.query_params.get("category")
        if category not in ("offline", "health", "error"):
            category = None

        return Response(
            {
                "results": get_problem_alerts(
                    limit=limit, active_only=active_only, category=category
                )
            }
        )


class DetectionsView(APIView):
    """
    Real-world events reported by cameras over MQTT (e.g. smoke, person,
    or other AI-detected events). This is a plain chronological event log
    — detections don't have an "active/resolved" lifecycle the way
    problems do, so there's no active_only filter here.

    Endpoint:

        GET /api/detections/?limit=100
    """

    def get(self, request):
        limit = _clamp_limit(request, default=100, maximum=500)

        return Response({"results": get_camera_detections(limit=limit)})


class DeviceAlertResolveView(APIView):
    """
    Manually resolve a DeviceAlert (an offline alert, a health alert, or a
    device error) from the dashboard/alerts/device-detail UI.

    Endpoint:

        POST /api/alerts/device/<id>/resolve/

    This just sets active=False/resolved_at like any other resolution, so
    it drops out of every active-only view immediately. If the same
    problem is reported again over MQTT, the monitoring services create
    (or reuse) a fresh active alert the normal way -- a manual resolve
    only silences the current occurrence, it doesn't suppress the alert
    type forever.
    """

    def post(self, request, alert_id):
        alert = get_object_or_404(DeviceAlert, pk=alert_id)

        if alert.active:
            now = timezone.now()
            alert.active = False
            alert.resolved_at = now
            alert.manually_resolved_at = now
            alert.save(update_fields=["active", "resolved_at", "manually_resolved_at"])

        return Response({"id": alert.id, "active": alert.active})


class CameraAlertResolveView(APIView):
    """
    Manually resolve a CameraAlert -- a camera error/offline alert, or a
    real detection (CAMERA_ALERT) -- from the dashboard/alerts/camera-detail
    UI. See DeviceAlertResolveView for the resolve semantics; the same
    "reappears if MQTT reports it again" logic applies to detections too,
    since each detection is its own row.

    Endpoint:

        POST /api/alerts/camera/<id>/resolve/
    """

    def post(self, request, alert_id):
        alert = get_object_or_404(CameraAlert, pk=alert_id)

        if alert.active:
            now = timezone.now()
            alert.active = False
            alert.resolved_at = now
            alert.manually_resolved_at = now
            alert.save(update_fields=["active", "resolved_at", "manually_resolved_at"])

        return Response({"id": alert.id, "active": alert.active})

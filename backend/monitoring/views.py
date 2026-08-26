from rest_framework.response import Response
from rest_framework.views import APIView

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

        GET /api/problems/?limit=100&active_only=true

    active_only defaults to true: the backend reuses a single alert row
    while something stays broken, so this naturally shows one row per
    currently-broken device/camera. Pass active_only=false to also see
    resolved history (useful for a device that has flapped online/offline
    many times).
    """

    def get(self, request):
        limit = _clamp_limit(request, default=100, maximum=500)

        active_only = request.query_params.get("active_only", "true")
        active_only = str(active_only).lower() not in ("false", "0", "no")

        return Response({
            "results": get_problem_alerts(limit=limit, active_only=active_only),
        })


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

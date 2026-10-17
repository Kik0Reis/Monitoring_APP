from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.models import CameraAlert, DeviceAlert
from monitoring.services.alert_lists import get_camera_detections, get_problem_alerts
from monitoring.services.dashboard import get_dashboard_data
from monitoring.services.scope import hide_inactive_from_request
from monitoring.services.tree import get_monitor_tree

PROBLEM_CATEGORIES = ("offline", "health", "error")


# reads ?limit= from the request and keeps it between 1 and the maximum
def _clamp_limit(request, default, maximum):
    try:
        limit = int(request.query_params.get("limit", default))
    except (TypeError, ValueError):
        limit = default

    return max(1, min(limit, maximum))


# GET /api/dashboard/?scope=active|all returns everything the dashboard page shows
class DashboardView(APIView):
    # returns the dashboard payload
    def get(self, request):
        return Response(get_dashboard_data(hide_inactive=hide_inactive_from_request(request)))


# GET /api/problems/?limit=&active_only=&category=&scope= returns device and camera problems
# active_only (default true) hides resolved alerts, category is offline, health or error
class ProblemsView(APIView):
    # returns the problems list
    def get(self, request):
        unresolved_only = request.query_params.get("active_only", "true").lower() not in ("false", "0", "no")

        category = request.query_params.get("category")
        if category not in PROBLEM_CATEGORIES:
            category = None

        alerts = get_problem_alerts(
            limit=_clamp_limit(request, default=100, maximum=500),
            unresolved_only=unresolved_only,
            category=category,
            hide_inactive=hide_inactive_from_request(request),
        )
        return Response({"results": alerts})


# GET /api/detections/?limit=&scope= returns the events reported by cameras, newest first
class DetectionsView(APIView):
    # returns the detections list
    def get(self, request):
        detections = get_camera_detections(
            limit=_clamp_limit(request, default=100, maximum=500),
            hide_inactive=hide_inactive_from_request(request),
        )
        return Response({"results": detections})


# base view that manually resolves one alert, subclasses only set the alert model
class AlertResolveView(APIView):
    alert_model = None

    # resolves the alert if it is still active
    def post(self, request, alert_id):
        alert = get_object_or_404(self.alert_model, pk=alert_id)

        if alert.active:
            now = timezone.now()
            alert.active = False
            alert.resolved_at = now
            alert.manually_resolved_at = now
            alert.save(update_fields=["active", "resolved_at", "manually_resolved_at"])

        return Response({"id": alert.id, "active": alert.active})


# POST /api/alerts/device/<id>/resolve/ resolves a device alert
class DeviceAlertResolveView(AlertResolveView):
    alert_model = DeviceAlert


# POST /api/alerts/camera/<id>/resolve/ resolves a camera alert or detection
class CameraAlertResolveView(AlertResolveView):
    alert_model = CameraAlert


# GET /api/monitor/tree/?scope=active|all returns the Country > Customer > Location > Device > Camera tree
class MonitorTreeView(APIView):
    # returns the monitor tree
    def get(self, request):
        return Response({"results": get_monitor_tree(hide_inactive=hide_inactive_from_request(request))})

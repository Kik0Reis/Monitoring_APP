from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.services.dashboard import get_dashboard_data, get_recent_alerts


class DashboardView(APIView):
    """
    Monitoring dashboard API.

    Provides aggregated monitoring information for the frontend.

    Endpoint:

        GET /api/dashboard/

    Returns:

        - device summary
        - recent alerts
        - devices with active problems (click through to the device)
        - locations with active problems (click through to the location)

    All aggregation logic lives in monitoring.services.dashboard so there
    is exactly one implementation to keep in sync with the frontend.
    """

    def get(self, request):
        return Response(get_dashboard_data())


class AlertsView(APIView):
    """
    Full alerts feed (device + camera alerts merged), newest first.

    Endpoint:

        GET /api/alerts/?limit=100

    Powers the "Alerts" page, which previously did not exist.
    """

    def get(self, request):
        limit = request.query_params.get("limit", 100)

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 100

        limit = max(1, min(limit, 500))

        return Response({"results": get_recent_alerts(limit=limit)})

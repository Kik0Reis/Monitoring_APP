from rest_framework.routers import DefaultRouter, path

from cameras.views import CameraViewSet
from core.views import SettingsView
from countries.views import CountryViewSet
from customers.views import CustomerViewSet
from devices.views import DeviceViewSet
from locations.views import LocationViewSet
from monitoring.views import (
    CameraAlertResolveView,
    DashboardView,
    DetectionsView,
    DeviceAlertResolveView,
    MonitorTreeView,
    ProblemsView,
)

router = DefaultRouter()

# All the endpoints for the API are registered here. The router will automatically generate the URL patterns for each viewset.

router.register("countries", CountryViewSet)
router.register("customers", CustomerViewSet)
router.register("locations", LocationViewSet)
router.register("devices", DeviceViewSet)
router.register("cameras", CameraViewSet)


urlpatterns = [
    *router.urls,
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # Full Country > Customer > Location > Device > Camera tree for the
    # "Monitor > Views" page, with per-node status/alerts/detections rollup.
    path("monitor/tree/", MonitorTreeView.as_view(), name="monitor-tree"),
    # Device/camera health & connectivity problems (offline, unhealthy
    # component, MQTT/system errors, camera errors).
    path("problems/", ProblemsView.as_view(), name="problems"),
    # Real camera detections reported over MQTT (smoke, person, etc.).
    path("detections/", DetectionsView.as_view(), name="detections"),
    # Manually mark a DeviceAlert/CameraAlert as resolved (dashboard,
    # alerts page, device/camera detail pages). Reappears as a fresh
    # active alert if the same problem is re-reported on MQTT.
    path(
        "alerts/device/<int:alert_id>/resolve/",
        DeviceAlertResolveView.as_view(),
        name="device-alert-resolve",
    ),
    path(
        "alerts/camera/<int:alert_id>/resolve/",
        CameraAlertResolveView.as_view(),
        name="camera-alert-resolve",
    ),
    # Reads/writes backend/.env directly (see core/env_settings.py).
    path("settings/", SettingsView.as_view(), name="app-settings"),
]

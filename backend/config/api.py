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

# api routes, the router creates the list and detail urls of each viewset

router.register("countries", CountryViewSet)
router.register("customers", CustomerViewSet)
router.register("locations", LocationViewSet)
router.register("devices", DeviceViewSet)
router.register("cameras", CameraViewSet)


urlpatterns = [
    *router.urls,
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # tree of country > customer > location > device > camera with the status of each node
    path("monitor/tree/", MonitorTreeView.as_view(), name="monitor-tree"),
    # problems of devices and cameras (offline, unhealthy components, errors)
    path("problems/", ProblemsView.as_view(), name="problems"),
    # events detected by the cameras
    path("detections/", DetectionsView.as_view(), name="detections"),
    # marks an alert as resolved, it is created again if the problem is reported again
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
    # settings stored in the .env file
    path("settings/", SettingsView.as_view(), name="app-settings"),
]

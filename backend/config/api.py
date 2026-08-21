from rest_framework.routers import DefaultRouter, path

from monitoring.views import AlertsView, DashboardView
from countries.views import CountryViewSet
from customers.views import CustomerViewSet
from locations.views import LocationViewSet
from devices.views import DeviceViewSet
from cameras.views import CameraViewSet

router = DefaultRouter()

# All the endpoints for the API are registered here. The router will automatically generate the URL patterns for each viewset.

router.register("countries", CountryViewSet)
router.register("customers", CustomerViewSet)
router.register("locations", LocationViewSet)
router.register("devices", DeviceViewSet)
router.register("cameras", CameraViewSet)


urlpatterns = [
    *router.urls,

    path(
        "dashboard/",
        DashboardView.as_view(),
        name="dashboard",
    ),

    path(
        "alerts/",
        AlertsView.as_view(),
        name="alerts",
    ),
]
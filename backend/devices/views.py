from django.db.models import Count

from core.viewsets import ApprovableModelViewSet

from .models import Device
from .serializers import DeviceSerializer


# crud api for devices
class DeviceViewSet(ApprovableModelViewSet):
    queryset = (
        Device.objects.select_related("location", "location__customer", "location__customer__country")
        .prefetch_related("alerts")
        .annotate(cameras_count_annotation=Count("cameras", distinct=True))
    )
    serializer_class = DeviceSerializer
    filterset_fields = ["location", "status", "active", "pending_review"]
    search_fields = ["name", "serial_number", "mqtt_identifier"]
    ordering_fields = ["name", "last_seen", "created_at"]

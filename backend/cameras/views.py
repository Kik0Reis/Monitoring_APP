from core.viewsets import ApprovableModelViewSet

from .models import Camera
from .serializers import CameraSerializer


# crud api for cameras
class CameraViewSet(ApprovableModelViewSet):
    queryset = Camera.objects.select_related(
        "device",
        "device__location",
        "device__location__customer",
        "device__location__customer__country",
    ).prefetch_related("alerts")
    serializer_class = CameraSerializer
    filterset_fields = ["device", "status", "active", "channel", "pending_review"]
    search_fields = ["name", "camera_identifier", "device__name", "device__mqtt_identifier"]
    ordering_fields = ["name", "channel", "status", "last_seen", "created_at"]

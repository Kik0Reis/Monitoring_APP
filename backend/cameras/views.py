from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Camera
from .serializers import CameraSerializer


class CameraViewSet(viewsets.ModelViewSet):
    """CRUD API for cameras, plus an `approve` action for auto-created ones."""

    queryset = Camera.objects.select_related(
        "device",
        "device__location",
        "device__location__customer",
        "device__location__customer__country",
    ).prefetch_related("alerts")

    serializer_class = CameraSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["device", "status", "active", "channel", "pending_review"]

    search_fields = [
        "name",
        "camera_identifier",
        "device__name",
        "device__mqtt_identifier",
    ]

    ordering_fields = ["name", "channel", "status", "last_seen", "created_at"]

    ordering = ["name"]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Clear pending_review on a camera that was auto-created from an
        MQTT topic, confirming a human has looked at it.
        """

        camera = self.get_object()
        camera.pending_review = False
        camera.save(update_fields=["pending_review", "updated_at"])

        return Response(self.get_serializer(camera).data)

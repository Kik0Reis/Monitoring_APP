from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import Camera
from .serializers import CameraSerializer


class CameraViewSet(viewsets.ModelViewSet):
    queryset = Camera.objects.select_related(
        "device",
        "device__location",
        "device__location__customer",
        "device__location__customer__country",
    )

    serializer_class = CameraSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "device",
        "status",
        "active",
        "channel",
    ]

    search_fields = [
        "name",
        "camera_identifier",
        "device__name",
        "device__mqtt_identifier",
    ]

    ordering_fields = [
        "name",
        "channel",
        "status",
        "last_seen",
        "created_at",
    ]

    ordering = [
        "name",
    ]
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Device
from .serializers import DeviceSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    """CRUD API for devices, plus an `approve` action for auto-created ones."""

    queryset = Device.objects.select_related(
        "location", "location__customer", "location__customer__country"
    ).annotate(cameras_count_annotation=Count("cameras", distinct=True))

    serializer_class = DeviceSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["location", "status", "active", "pending_review"]

    search_fields = ["name", "serial_number", "mqtt_identifier"]

    ordering_fields = ["name", "last_seen", "created_at"]

    ordering = ["name"]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Clear pending_review on a device that was auto-created from an
        MQTT topic, confirming a human has looked at it (typically after
        also giving it a real name and serial number).
        """

        device = self.get_object()
        device.pending_review = False
        device.save(update_fields=["pending_review", "updated_at"])

        return Response(self.get_serializer(device).data)

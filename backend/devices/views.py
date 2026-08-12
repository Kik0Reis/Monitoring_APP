from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import Device
from .serializers import DeviceSerializer


class DeviceViewSet(viewsets.ModelViewSet):

    queryset = Device.objects.select_related(
        "location",
        "location__customer",
        "location__customer__country",
    )

    serializer_class = DeviceSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "location",
        "status",
        "active",
    ]

    search_fields = [
        "name",
        "serial_number",
        "mqtt_identifier",
    ]

    ordering_fields = [
        "name",
        "last_seen",
        "created_at",
    ]

    ordering = [
        "name",
    ]
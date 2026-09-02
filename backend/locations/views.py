from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Location
from .serializers import LocationSerializer


class LocationViewSet(viewsets.ModelViewSet):
    """CRUD API for locations, plus an `approve` action for auto-created ones."""

    queryset = Location.objects.select_related(
        "customer", "customer__country"
    ).annotate(devices_count_annotation=Count("devices", distinct=True))

    serializer_class = LocationSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["customer", "active", "pending_review"]

    search_fields = ["name", "description"]

    ordering_fields = ["name", "created_at"]

    ordering = ["name"]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Clear pending_review on a location that was auto-created from an
        MQTT topic, confirming a human has looked at it.
        """

        location = self.get_object()
        location.pending_review = False
        location.save(update_fields=["pending_review", "updated_at"])

        return Response(self.get_serializer(location).data)

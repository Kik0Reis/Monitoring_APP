from django.db.models import Count

from core.viewsets import ApprovableModelViewSet

from .models import Location
from .serializers import LocationSerializer


# crud api for locations
class LocationViewSet(ApprovableModelViewSet):
    queryset = Location.objects.select_related("customer", "customer__country").annotate(
        devices_count_annotation=Count("devices", distinct=True)
    )
    serializer_class = LocationSerializer
    filterset_fields = ["customer", "active", "pending_review"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]

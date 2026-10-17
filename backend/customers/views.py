from django.db.models import Count

from core.viewsets import ApprovableModelViewSet

from .models import Customer
from .serializers import CustomerSerializer


# crud api for customers
class CustomerViewSet(ApprovableModelViewSet):
    queryset = Customer.objects.select_related("country").annotate(
        locations_count_annotation=Count("locations", distinct=True)
    )
    serializer_class = CustomerSerializer
    filterset_fields = ["country", "active", "pending_review"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]

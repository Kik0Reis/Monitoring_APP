from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """CRUD API for customers, plus an `approve` action for auto-created ones."""

    queryset = Customer.objects.select_related("country").annotate(
        locations_count_annotation=Count("locations", distinct=True)
    )

    serializer_class = CustomerSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["country", "active", "pending_review"]

    search_fields = ["name", "description"]

    ordering_fields = ["name", "created_at"]

    ordering = ["name"]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Clear pending_review on a customer that was auto-created from an
        MQTT topic, confirming a human has looked at it.
        """

        customer = self.get_object()
        customer.pending_review = False
        customer.save(update_fields=["pending_review", "updated_at"])

        return Response(self.get_serializer(customer).data)

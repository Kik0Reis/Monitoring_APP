from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Country
from .serializers import CountrySerializer


class CountryViewSet(viewsets.ModelViewSet):
    # Annotate the number of customers per country so the serializer can
    # expose "customers_count" without an extra query per row. This is what
    # powers the drilldown cards on the frontend (Country -> Customers).
    queryset = Country.objects.annotate(
        customers_count_annotation=Count("customers", distinct=True),
    )

    serializer_class = CountrySerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "pending_review",
    ]

    search_fields = [
        "name",
        "code",
    ]

    ordering_fields = [
        "name",
        "created_at",
    ]

    ordering = [
        "name",
    ]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Clear pending_review on a country that was auto-created from an
        MQTT topic, confirming a human has looked at it.
        """

        country = self.get_object()
        country.pending_review = False
        country.save(update_fields=["pending_review", "updated_at"])

        return Response(self.get_serializer(country).data)

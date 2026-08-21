from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

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

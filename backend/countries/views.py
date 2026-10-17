from django.db.models import Count

from core.viewsets import ApprovableModelViewSet

from .models import Country
from .serializers import CountrySerializer


# crud api for countries
class CountryViewSet(ApprovableModelViewSet):
    queryset = Country.objects.annotate(customers_count_annotation=Count("customers", distinct=True))
    serializer_class = CountrySerializer
    filterset_fields = ["pending_review"]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]

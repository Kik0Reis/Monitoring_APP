from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


# base crud viewset with filtering, search, ordering and an approve action for records created from mqtt
class ApprovableModelViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ["name"]

    # clears pending_review after a person confirmed a record that was created from mqtt
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        record = self.get_object()
        record.pending_review = False
        record.save(update_fields=["pending_review", "updated_at"])

        return Response(self.get_serializer(record).data)

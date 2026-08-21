from rest_framework import serializers

from countries.models import Country
from countries.serializers import CountrySummarySerializer

from .models import Customer


# Serializer responsible for validating and serializing Customer objects.
class CustomerSerializer(serializers.ModelSerializer):
    # Nested country information returned in responses.
    country = CountrySummarySerializer(
        read_only=True,
    )

    # Country ID used when creating or updating a customer.
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        source="country",
        write_only=True,
    )

    # Number of locations that belong to this customer.
    locations_count = serializers.SerializerMethodField()

    # Breadcrumb trail used by the frontend to render drilldown
    # navigation (Country -> Customer) without extra API calls.
    breadcrumb = serializers.SerializerMethodField()

    class Meta:
        model = Customer

        fields = (
            "id",
            "country",
            "country_id",
            "name",
            "description",
            "active",
            "locations_count",
            "breadcrumb",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def get_locations_count(self, obj):
        annotated = getattr(obj, "locations_count_annotation", None)

        if annotated is not None:
            return annotated

        return obj.locations.count()

    def get_breadcrumb(self, obj):
        return [
            {
                "type": "country",
                "id": obj.country_id,
                "name": obj.country.name,
                "path": f"/countries/{obj.country_id}",
            },
            {
                "type": "customer",
                "id": obj.id,
                "name": obj.name,
                "path": f"/clients/{obj.id}",
            },
        ]

    def validate_name(self, value):
        """
        Validate the customer name.

        Remove whitespace.
        Ensure the name has at least 2 characters.
        """

        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Customer name must contain at least 2 characters."
            )

        return value

    def validate_description(self, value):
        """
        Remove whitespace from the description.
        """

        return value.strip()


class CustomerSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer used when Customer is nested
    inside another serializer.
    """

    class Meta:
        model = Customer
        fields = (
            "id",
            "name",
        )

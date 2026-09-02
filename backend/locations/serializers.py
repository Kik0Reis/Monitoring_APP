from rest_framework import serializers

from customers.models import Customer
from customers.serializers import CustomerSummarySerializer

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    """Validates and (de)serializes Location records for the API."""

    # Nested customer information returned in responses.
    customer = CustomerSummarySerializer(read_only=True)

    # Customer ID used when creating or updating a location.
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), source="customer", write_only=True
    )

    # Number of devices that belong to this location.
    devices_count = serializers.SerializerMethodField()

    # Breadcrumb trail used by the frontend to render drilldown
    # navigation (Country -> Customer -> Location).
    breadcrumb = serializers.SerializerMethodField()

    class Meta:
        model = Location

        fields = (
            "id",
            "customer",
            "customer_id",
            "name",
            "description",
            "active",
            "devices_count",
            "breadcrumb",
            "pending_review",
            "created_at",
            "updated_at",
        )

        read_only_fields = ("id", "pending_review", "created_at", "updated_at")

    def get_devices_count(self, obj):
        annotated = getattr(obj, "devices_count_annotation", None)

        if annotated is not None:
            return annotated

        return obj.devices.count()

    def get_breadcrumb(self, obj):
        customer = obj.customer

        trail = []

        # customer.country isn't always select_related()'d by the caller,
        # so this can trigger an extra query — acceptable here since
        # breadcrumbs are only built for single-object responses.
        country = customer.country

        trail.append(
            {
                "type": "country",
                "id": country.id,
                "name": country.name,
                "path": f"/countries/{country.id}",
            }
        )

        trail.append(
            {
                "type": "customer",
                "id": customer.id,
                "name": customer.name,
                "path": f"/clients/{customer.id}",
            }
        )

        trail.append(
            {
                "type": "location",
                "id": obj.id,
                "name": obj.name,
                "path": f"/locations/{obj.id}",
            }
        )

        return trail

    def validate_name(self, value):
        """Trim whitespace and require at least 2 characters."""

        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Location name must contain at least 2 characters."
            )

        return value

    def validate_description(self, value):
        """Trim whitespace from the description."""

        return value.strip()

    def validate(self, attrs):
        """Reject locations being assigned to an inactive customer."""

        customer = attrs.get("customer")

        if customer and not customer.active:
            raise serializers.ValidationError(
                {"customer_id": "Cannot assign a location to an inactive customer."}
            )

        return attrs


class LocationSummarySerializer(serializers.ModelSerializer):
    """Minimal Location fields, for nesting inside other serializers."""

    class Meta:
        model = Location
        fields = ("id", "name")

from rest_framework import serializers

from customers.models import Customer
from customers.serializers import CustomerSummarySerializer

from .models import Location


# Serializer responsible for validating and serializing Location objects.
class LocationSerializer(serializers.ModelSerializer):
    # Nested customer information returned in responses.
    customer = CustomerSummarySerializer(
        read_only=True,
    )

    # Customer ID used when creating or updating a location.
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(),
        source="customer",
        write_only=True,
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
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def get_devices_count(self, obj):
        annotated = getattr(obj, "devices_count_annotation", None)

        if annotated is not None:
            return annotated

        return obj.devices.count()

    def get_breadcrumb(self, obj):
        customer = obj.customer

        trail = []

        # customer.country may not be select_related()'d in every context;
        # guard against the extra query being unavoidable in that case.
        country = customer.country

        trail.append({
            "type": "country",
            "id": country.id,
            "name": country.name,
            "path": f"/countries/{country.id}",
        })

        trail.append({
            "type": "customer",
            "id": customer.id,
            "name": customer.name,
            "path": f"/clients/{customer.id}",
        })

        trail.append({
            "type": "location",
            "id": obj.id,
            "name": obj.name,
            "path": f"/locations/{obj.id}",
        })

        return trail

    def validate_name(self, value):
        """
        Validate the location name.

        Remove whitespace.
        Make sure the name has at least 2 characters.
        """

        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Location name must contain at least 2 characters."
            )

        return value

    def validate_description(self, value):
        """
        Remove whitespace from the description.
        """

        return value.strip()

    def validate(self, attrs):
        """
        Validate business rules involving multiple fields.

        Prevent creating locations under inactive customers.
        """

        customer = attrs.get("customer")

        if customer and not customer.active:
            raise serializers.ValidationError(
                {
                    "customer_id": (
                        "Cannot assign a location to an inactive customer."
                    )
                }
            )

        return attrs


class LocationSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer used when Location is nested
    inside another serializer.
    """

    class Meta:
        model = Location
        fields = (
            "id",
            "name",
        )

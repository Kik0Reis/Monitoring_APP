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

    class Meta:
        model = Location

        fields = (
            "id",
            "customer",
            "customer_id",
            "name",
            "description",
            "active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

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
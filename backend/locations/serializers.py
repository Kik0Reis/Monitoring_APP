from rest_framework import serializers

from core.breadcrumbs import location_breadcrumb
from core.serializer_helpers import annotated_count, clean_name
from customers.models import Customer
from customers.serializers import CustomerSummarySerializer

from .models import Location


# validates and converts location records for the api
class LocationSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), source="customer", write_only=True
    )
    devices_count = serializers.SerializerMethodField()
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

    # returns how many devices belong to the location
    def get_devices_count(self, obj):
        return annotated_count(obj, "devices_count_annotation", "devices")

    # returns the navigation trail country > customer > location
    def get_breadcrumb(self, obj):
        return location_breadcrumb(obj)

    # trims the name and requires at least 2 characters
    def validate_name(self, value):
        return clean_name(value, "Location name")

    # trims the description
    def validate_description(self, value):
        return value.strip()

    # does not allow a location to be assigned to an inactive customer
    def validate(self, attrs):
        customer = attrs.get("customer")

        if customer and not customer.active:
            raise serializers.ValidationError(
                {"customer_id": "Cannot assign a location to an inactive customer."}
            )

        return attrs


# minimal location fields to nest inside other serializers
class LocationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ("id", "name")

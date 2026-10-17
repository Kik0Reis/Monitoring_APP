from rest_framework import serializers

from core.breadcrumbs import customer_breadcrumb
from core.serializer_helpers import annotated_count, clean_name
from countries.models import Country
from countries.serializers import CountrySummarySerializer

from .models import Customer


# validates and converts customer records for the api
class CustomerSerializer(serializers.ModelSerializer):
    country = CountrySummarySerializer(read_only=True)
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), source="country", write_only=True
    )
    locations_count = serializers.SerializerMethodField()
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
            "pending_review",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "pending_review", "created_at", "updated_at")

    # returns how many locations belong to the customer
    def get_locations_count(self, obj):
        return annotated_count(obj, "locations_count_annotation", "locations")

    # returns the navigation trail country > customer
    def get_breadcrumb(self, obj):
        return customer_breadcrumb(obj)

    # trims the name and requires at least 2 characters
    def validate_name(self, value):
        return clean_name(value, "Customer name")

    # trims the description
    def validate_description(self, value):
        return value.strip()


# minimal customer fields to nest inside other serializers
class CustomerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "name")

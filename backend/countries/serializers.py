from rest_framework import serializers

from core.serializer_helpers import annotated_count, clean_name

from .models import Country


# validates and converts country records for the api
class CountrySerializer(serializers.ModelSerializer):
    customers_count = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = (
            "id",
            "name",
            "code",
            "customers_count",
            "pending_review",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "pending_review", "created_at", "updated_at")

    # returns how many customers belong to the country
    def get_customers_count(self, obj):
        return annotated_count(obj, "customers_count_annotation", "customers")

    # trims the name and requires at least 2 characters
    def validate_name(self, value):
        return clean_name(value, "Country name")

    # trims the code, makes it uppercase and requires exactly 2 characters
    def validate_code(self, value):
        value = value.strip().upper()

        if len(value) != 2:
            raise serializers.ValidationError("Country code must contain exactly 2 characters.")

        return value


# minimal country fields to nest inside other serializers
class CountrySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("id", "name", "code")

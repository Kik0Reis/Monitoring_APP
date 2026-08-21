from rest_framework import serializers

from .models import Country


# Serializer responsible for validating and serializing Country objects.
class CountrySerializer(serializers.ModelSerializer):

    # Number of customers that belong to this country.
    # Uses the "customers_count_annotation" annotation added by
    # CountryViewSet when present, otherwise falls back to a live query
    # so the field always works even outside that viewset.
    customers_count = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = (
            "id",
            "name",
            "code",
            "customers_count",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def get_customers_count(self, obj):
        annotated = getattr(obj, "customers_count_annotation", None)

        if annotated is not None:
            return annotated

        return obj.customers.count()

    def validate_name(self, value):
        """
        Validate the country name.

        Remove whitespace.
        Make sure the name has at least 2 charaters.
        """

        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Country name must contain at least 2 characters."
            )

        return value

    def validate_code(self, value):
        """
        Validate the country code.

        Remove whitespace.
        Convert the code to uppercase.
        Ensure the code has 2 characters.
        """

        value = value.strip().upper()

        if len(value) != 2:
            raise serializers.ValidationError(
                "Country code must contain exactly 2 characters."
            )

        return value


class CountrySummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer used when Country is nested
    inside another serializer.
    """

    class Meta:
        model = Country
        fields = (
            "id",
            "name",
            "code",
        )

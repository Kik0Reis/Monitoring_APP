from rest_framework import serializers
from .models import Country
from .models import Customer
from countries.serializers import CountrySerializer


class CustomerSerializer(serializers.ModelSerializer):

    country = CountrySerializer(read_only=True)
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        source="country",
        write_only=True,
    )

    class Meta:
        model = Customer

        fields = (
            "id",
            "country",
            "country_id",
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
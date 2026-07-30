from rest_framework import serializers
from .models import Customer
from .models import Location
from customers.serializers import CustomerSerializer


class LocationSerializer(serializers.ModelSerializer):

    customer = CustomerSerializer(read_only=True)

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
from rest_framework import serializers
from locations.serializers import LocationSerializer
from .models import Location
from .models import Device


class DeviceSerializer(serializers.ModelSerializer):

    location = LocationSerializer(read_only=True)

    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        source="location",
        write_only=True,
    )

    class Meta:
        model = Device

        fields = (
            "id",
            "location",
            "location_id",
            "name",
            "mqtt_identifier",
            "serial_number",
            "status",
            "last_seen",
            "active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "last_seen",
        )
from rest_framework import serializers

from locations.models import Location
from locations.serializers import LocationSummarySerializer

from .models import Device


class DeviceSerializer(serializers.ModelSerializer):

    location = LocationSummarySerializer(
        read_only=True,
    )

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
            "device_type",
            "status",
            "last_seen",
            "active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "device_type",
            "status",
            "last_seen",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Device name must contain at least 2 characters."
            )

        return value

    def validate_mqtt_identifier(self, value):
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "MQTT identifier must contain at least 3 characters."
            )

        return value

    def validate_serial_number(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        location = attrs.get("location")

        if location and not location.active:
            raise serializers.ValidationError(
                {
                    "location_id": (
                        "Cannot assign a device to an inactive location."
                    )
                }
            )

        return attrs
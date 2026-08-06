from rest_framework import serializers

from locations.models import Location
from locations.serializers import LocationSummarySerializer

from .models import Device


# Serializer responsible for validating and serializing Device objects.
class DeviceSerializer(serializers.ModelSerializer):
    # Nested location information returned in responses.
    location = LocationSummarySerializer(
        read_only=True,
    )

    # Location ID used when creating or updating a device.
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
            "status",
            "last_seen",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        """
        Validate the device name.
        """

        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Device name must contain at least 2 characters."
            )

        return value

    def validate_mqtt_identifier(self, value):
        """
        Validate and normalize the MQTT identifier.
        """

        value = value.strip().upper()

        if len(value) < 3:
            raise serializers.ValidationError(
                "MQTT identifier must contain at least 3 characters."
            )

        return value

    def validate_serial_number(self, value):
        """
        Validate and normalize the serial number.
        """

        return value.strip().upper()

    def validate(self, attrs):
        """
        Prevent creating devices under inactive locations.
        """

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
from rest_framework import serializers

from devices.models import Device

from .models import Camera


class CameraSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(
        source="device.name",
        read_only=True,
    )

    device_id = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.filter(
            active=True,
            device_type="EDGE",
        ),
        source="device",
        write_only=True,
    )

    class Meta:
        model = Camera

        fields = (
            "id",
            "device",
            "device_id",
            "device_name",
            "name",
            "camera_identifier",
            "channel",
            "status",
            "last_seen",
            "active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "device",
            "device_name",
            "status",
            "last_seen",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Camera name must contain at least 2 characters."
            )

        return value

    def validate_camera_identifier(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Camera identifier must contain at least 2 characters."
            )

        return value

    def validate_channel(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Camera channel must be greater than zero."
            )

        return value

    def validate(self, attrs):
        device = attrs.get("device")

        if device is None:
            return attrs

        if not device.active:
            raise serializers.ValidationError(
                {
                    "device_id": (
                        "Cannot assign a camera to an inactive device."
                    )
                }
            )

        if device.device_type != "EDGE":
            raise serializers.ValidationError(
                {
                    "device_id": (
                        "A camera can only be connected to "
                        "an Edge device."
                    )
                }
            )

        return attrs
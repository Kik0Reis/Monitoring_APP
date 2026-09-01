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

    # Breadcrumb trail used by the frontend to render drilldown
    # navigation (Country -> Customer -> Location -> Device -> Camera).
    breadcrumb = serializers.SerializerMethodField()

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
            "breadcrumb",
            "pending_review",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "device",
            "device_name",
            "status",
            "last_seen",
            "pending_review",
            "created_at",
            "updated_at",
        )

    def get_breadcrumb(self, obj):
        device = obj.device
        location = device.location
        customer = location.customer
        country = customer.country

        return [
            {
                "type": "country",
                "id": country.id,
                "name": country.name,
                "path": f"/countries/{country.id}",
            },
            {
                "type": "customer",
                "id": customer.id,
                "name": customer.name,
                "path": f"/clients/{customer.id}",
            },
            {
                "type": "location",
                "id": location.id,
                "name": location.name,
                "path": f"/locations/{location.id}",
            },
            {
                "type": "device",
                "id": device.id,
                "name": device.name,
                "path": f"/devices/{device.id}",
            },
            {
                "type": "camera",
                "id": obj.id,
                "name": obj.name,
                "path": f"/cameras/{obj.id}",
            },
        ]

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
                {"device_id": ("Cannot assign a camera to an inactive device.")}
            )

        if device.device_type != "EDGE":
            raise serializers.ValidationError(
                {"device_id": ("A camera can only be connected to " "an Edge device.")}
            )

        return attrs

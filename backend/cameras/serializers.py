from rest_framework import serializers

from core.alert_rules import alert_summary, detection_cutoff, is_alert_visible
from core.breadcrumbs import camera_breadcrumb
from core.serializer_helpers import clean_name
from devices.models import Device

from .models import Camera

MAX_ALERTS_SHOWN = 30


# validates and converts camera records for the api
class CameraSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    device_id = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.filter(active=True, device_type="EDGE"),
        source="device",
        write_only=True,
    )
    breadcrumb = serializers.SerializerMethodField()

    # problems of the camera (error and offline), detections are in their own field
    alerts = serializers.SerializerMethodField()
    detections = serializers.SerializerMethodField()

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
            "on_mqtt",
            "serial_number",
            "latitude",
            "longitude",
            "health_data",
            "license_data",
            "active",
            "breadcrumb",
            "alerts",
            "detections",
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
            "on_mqtt",
            "serial_number",
            "latitude",
            "longitude",
            "health_data",
            "license_data",
            "alerts",
            "detections",
            "pending_review",
            "created_at",
            "updated_at",
        )

    # returns the navigation trail country > customer > location > device > camera
    def get_breadcrumb(self, obj):
        return camera_breadcrumb(obj)

    # returns the newest problems of the camera, detections and expired errors are left out
    def get_alerts(self, obj):
        return [
            alert_summary(alert)
            for alert in obj.alerts.all()
            if alert.alert_type != "CAMERA_ALERT" and is_alert_visible(alert.alert_type, alert.created_at)
        ][:MAX_ALERTS_SHOWN]

    # returns the newest detections of the camera that are active and not expired
    def get_detections(self, obj):
        cutoff = detection_cutoff()

        return [
            alert_summary(alert)
            for alert in obj.alerts.all()
            if alert.alert_type == "CAMERA_ALERT" and alert.active and alert.created_at >= cutoff
        ][:MAX_ALERTS_SHOWN]

    # trims the name and requires at least 2 characters
    def validate_name(self, value):
        return clean_name(value, "Camera name")

    # trims the identifier and requires at least 2 characters
    def validate_camera_identifier(self, value):
        return clean_name(value, "Camera identifier")

    # requires the channel to be greater than zero
    def validate_channel(self, value):
        if value < 1:
            raise serializers.ValidationError("Camera channel must be greater than zero.")

        return value

    # only allows a camera on an active edge device
    def validate(self, attrs):
        device = attrs.get("device")

        if device is None:
            return attrs

        if not device.active:
            raise serializers.ValidationError({"device_id": "Cannot assign a camera to an inactive device."})

        if device.device_type != "EDGE":
            raise serializers.ValidationError({"device_id": "A camera can only be connected to an Edge device."})

        return attrs

from rest_framework import serializers

from core.alert_rules import alert_summary, is_alert_visible
from core.breadcrumbs import device_breadcrumb
from core.serializer_helpers import annotated_count, clean_name
from locations.models import Location
from locations.serializers import LocationSummarySerializer

from .models import Device

MAX_ALERTS_SHOWN = 30


# summary of the most recent heartbeat received from a device
class LatestHeartbeatSerializer(serializers.Serializer):
    received_at = serializers.DateTimeField()
    cpu = serializers.FloatField(allow_null=True)
    memory = serializers.FloatField(allow_null=True)
    storage = serializers.FloatField(allow_null=True)
    temperature = serializers.FloatField(allow_null=True)
    raw_payload = serializers.JSONField()


# validates and converts device records for the api
class DeviceSerializer(serializers.ModelSerializer):
    location = LocationSummarySerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), source="location", write_only=True
    )
    cameras_count = serializers.SerializerMethodField()
    breadcrumb = serializers.SerializerMethodField()
    latest_heartbeat = serializers.SerializerMethodField()
    alerts = serializers.SerializerMethodField()

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
            "on_mqtt",
            "active",
            "component_statuses",
            "health_data",
            "system_info",
            "latest_heartbeat",
            "cameras_count",
            "breadcrumb",
            "alerts",
            "pending_review",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "device_type",
            "status",
            "last_seen",
            "on_mqtt",
            "component_statuses",
            "health_data",
            "system_info",
            "alerts",
            "pending_review",
            "created_at",
            "updated_at",
        )

    # returns how many cameras are connected to the device
    def get_cameras_count(self, obj):
        return annotated_count(obj, "cameras_count_annotation", "cameras")

    # returns the navigation trail country > customer > location > device
    def get_breadcrumb(self, obj):
        return device_breadcrumb(obj)

    # returns the newest heartbeat of the device, or None when it has none
    def get_latest_heartbeat(self, obj):
        heartbeat = obj.heartbeats.first()
        return LatestHeartbeatSerializer(heartbeat).data if heartbeat else None

    # returns the newest alerts of the device, expired error alerts are left out
    def get_alerts(self, obj):
        return [
            alert_summary(alert)
            for alert in obj.alerts.all()
            if is_alert_visible(alert.alert_type, alert.created_at)
        ][:MAX_ALERTS_SHOWN]

    # trims the name and requires at least 2 characters
    def validate_name(self, value):
        return clean_name(value, "Device name")

    # trims the mqtt identifier, there is no minimum length
    def validate_mqtt_identifier(self, value):
        return value.strip()

    # trims the serial number and makes it uppercase
    def validate_serial_number(self, value):
        return value.strip().upper()

    # does not allow a device to be assigned to an inactive location
    def validate(self, attrs):
        location = attrs.get("location")

        if location and not location.active:
            raise serializers.ValidationError(
                {"location_id": "Cannot assign a device to an inactive location."}
            )

        return attrs

from rest_framework import serializers

from locations.models import Location
from locations.serializers import LocationSummarySerializer

from .models import Device


class LatestHeartbeatSerializer(serializers.Serializer):
    """
    Small summary of the most recent heartbeat received from a device.

    Kept separate from DeviceHeartbeat's own serializer (in monitoring)
    so devices/serializers.py does not need to import the monitoring app.
    """

    received_at = serializers.DateTimeField()
    cpu = serializers.FloatField(allow_null=True)
    memory = serializers.FloatField(allow_null=True)
    storage = serializers.FloatField(allow_null=True)
    temperature = serializers.FloatField(allow_null=True)
    # Full original MQTT health payload, in case it contains metrics or
    # component details that don't have a dedicated column yet.
    raw_payload = serializers.JSONField()


class DeviceSerializer(serializers.ModelSerializer):
    """Validates and (de)serializes Device records for the API."""

    location = LocationSummarySerializer(read_only=True)

    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), source="location", write_only=True
    )

    # Number of cameras connected to this device.
    cameras_count = serializers.SerializerMethodField()

    # Breadcrumb trail used by the frontend to render drilldown
    # navigation (Country -> Customer -> Location -> Device).
    breadcrumb = serializers.SerializerMethodField()

    # Most recent heartbeat metrics (cpu/memory/storage/temperature),
    # when the device has reported at least one heartbeat.
    latest_heartbeat = serializers.SerializerMethodField()

    # Recent alerts (active and resolved) for this device, newest first.
    # This is what powers the "what actually went wrong" view on the
    # device detail page instead of just a status badge.
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
            # Full internal component breakdown (detectorapi, detector,
            # idmr, ...) reported by the Edge device over MQTT.
            "component_statuses",
            # Raw payload of the most recent health message.
            "health_data",
            # Hardware/system info reported on info/edge-device (OS, CPU,
            # RAM, GPU, IP address, ...). Purely informational.
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

    def get_cameras_count(self, obj):
        annotated = getattr(obj, "cameras_count_annotation", None)

        if annotated is not None:
            return annotated

        return obj.cameras.count()

    def get_breadcrumb(self, obj):
        location = obj.location
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
                "id": obj.id,
                "name": obj.name,
                "path": f"/devices/{obj.id}",
            },
        ]

    def get_latest_heartbeat(self, obj):
        heartbeat = obj.heartbeats.first()

        if heartbeat is None:
            return None

        return LatestHeartbeatSerializer(heartbeat).data

    def get_alerts(self, obj):
        # DeviceAlert.Meta.ordering is already "-created_at", and the
        # view prefetches "alerts" so this doesn't add an extra query.
        #
        # "category" lets the frontend show these as separate sections:
        #   - "offline": DEVICE_OFFLINE (device currently unreachable).
        #   - "health":  DEVICE_HEALTH (component healthcheck failing).
        #   - "error":   DEVICE_ERROR/MQTT_ERROR/SYSTEM_ERROR -- a
        #     free-form message actually sent over MQTT (e.g. "low
        #     threshold"), not a status.
        def category(alert_type):
            if alert_type == "DEVICE_OFFLINE":
                return "offline"
            if alert_type == "DEVICE_HEALTH":
                return "health"
            return "error"

        return [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "category": category(alert.alert_type),
                "severity": alert.severity,
                "message": alert.message,
                "active": alert.active,
                "created_at": alert.created_at,
                "resolved_at": alert.resolved_at,
            }
            for alert in list(obj.alerts.all())[:30]
        ]

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
                {"location_id": "Cannot assign a device to an inactive location."}
            )

        return attrs

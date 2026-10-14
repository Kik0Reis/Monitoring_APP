from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from locations.models import Location
from locations.serializers import LocationSummarySerializer

from .models import Device

# Mirrors monitoring/services/dashboard.py:_stale_error_alert_q -- kept as
# a local copy of the same rule rather than importing the monitoring app
# here (see the LatestHeartbeatSerializer note above on keeping this
# module independent of it). If that rule ever changes, update both.
_ERROR_ALERT_TYPES = {"DEVICE_ERROR", "MQTT_ERROR", "SYSTEM_ERROR"}


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

        # An "error"-category alert stops counting as current after
        # settings.ALERT_VISIBLE_HOURS, same as everywhere else it's
        # shown (dashboard, alerts page, monitor tree) -- otherwise a
        # stale-but-still-active error would keep showing up here even
        # after it's disappeared everywhere else.
        visible_cutoff = timezone.now() - timezone.timedelta(hours=settings.ALERT_VISIBLE_HOURS)

        def is_visible(alert):
            if alert.alert_type in _ERROR_ALERT_TYPES:
                return alert.created_at >= visible_cutoff
            return True

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
            for alert in obj.alerts.all()
            if is_visible(alert)
        ][:30]

    def validate_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Device name must contain at least 2 characters."
            )

        return value

    def validate_mqtt_identifier(self, value):
        # Still required (an empty value is rejected by the field itself);
        # there is no minimum length.
        return value.strip()

    def validate_serial_number(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        location = attrs.get("location")

        if location and not location.active:
            raise serializers.ValidationError(
                {"location_id": "Cannot assign a device to an inactive location."}
            )

        return attrs

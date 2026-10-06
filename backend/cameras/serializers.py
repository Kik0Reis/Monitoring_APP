from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from devices.models import Device

from .models import Camera

# Mirrors monitoring/services/dashboard.py:_stale_error_alert_q /
# _detections_queryset -- kept as a local copy of the same rule rather
# than importing the monitoring app here, same reasoning as
# devices/serializers.py's _ERROR_ALERT_TYPES. If either rule changes,
# update all three places.
def _error_alert_visible_cutoff():
    return timezone.now() - timezone.timedelta(hours=settings.ALERT_VISIBLE_HOURS)


def _detection_visible_cutoff():
    return timezone.now() - timezone.timedelta(hours=settings.DETECTION_VISIBLE_HOURS)


class CameraSerializer(serializers.ModelSerializer):
    """Validates and (de)serializes Camera records for the API."""

    device_name = serializers.CharField(source="device.name", read_only=True)

    device_id = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.filter(active=True, device_type="EDGE"),
        source="device",
        write_only=True,
    )

    # Breadcrumb trail used by the frontend to render drilldown
    # navigation (Country -> Customer -> Location -> Device -> Camera).
    breadcrumb = serializers.SerializerMethodField()

    # Recent alerts (active and resolved) for this camera, newest first --
    # CAMERA_ERROR/CAMERA_OFFLINE only. Real detections (CAMERA_ALERT) are
    # a different thing and live in their own "detections" field below.
    alerts = serializers.SerializerMethodField()

    # Real-world detections (CAMERA_ALERT) reported by this camera,
    # newest first. Kept separate from "alerts" since these aren't
    # problems -- they're events (smoke, person, etc).
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
            # Per-component (detectorapi/detector/idmr) breakdown for this
            # specific camera, extracted from the device's health messages.
            "health_data",
            # Per-camera license status extracted from the device's
            # aiaction/.../info/licenses messages.
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

    def _serialize_alert(self, alert):
        return {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "category": "offline" if alert.alert_type == "CAMERA_OFFLINE" else "error",
            "severity": alert.severity,
            "message": alert.message,
            "active": alert.active,
            "created_at": alert.created_at,
            "resolved_at": alert.resolved_at,
        }

    def get_alerts(self, obj):
        # CameraAlert.Meta.ordering is already "-created_at", and the view
        # prefetches "alerts" so this doesn't add an extra query. Excludes
        # CAMERA_ALERT (real detections) -- see get_detections below.
        #
        # A CAMERA_ERROR alert stops counting as current after
        # settings.ALERT_VISIBLE_HOURS, same as everywhere else it's shown
        # (dashboard, alerts page, monitor tree) -- otherwise a
        # stale-but-still-active error would keep showing up here even
        # after it's disappeared everywhere else.
        error_cutoff = _error_alert_visible_cutoff()

        def is_visible(alert):
            if alert.alert_type == "CAMERA_OFFLINE":
                return True
            return alert.created_at >= error_cutoff

        return [
            self._serialize_alert(alert)
            for alert in obj.alerts.all()
            if alert.alert_type != "CAMERA_ALERT" and is_visible(alert)
        ][:30]

    def get_detections(self, obj):
        # Real-world events (CAMERA_ALERT), most recent first. Only
        # active, still-visible ones -- same active + DETECTION_VISIBLE_HOURS
        # window as get_camera_detections() in
        # monitoring/services/dashboard.py, so a resolved or aged-out
        # detection can't keep showing up here after it's gone from the
        # dashboard/alerts page.
        detections_cutoff = _detection_visible_cutoff()

        return [
            self._serialize_alert(alert)
            for alert in obj.alerts.all()
            if alert.alert_type == "CAMERA_ALERT"
            and alert.active
            and alert.created_at >= detections_cutoff
        ][:30]

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
                {"device_id": "Cannot assign a camera to an inactive device."}
            )

        if device.device_type != "EDGE":
            raise serializers.ValidationError(
                {"device_id": "A camera can only be connected to an Edge device."}
            )

        return attrs

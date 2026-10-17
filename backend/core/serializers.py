from rest_framework import serializers


# validates the settings sent to /api/settings/, an empty mqtt_password keeps the stored one
class AppSettingsSerializer(serializers.Serializer):
    mqtt_host = serializers.CharField(max_length=255, allow_blank=False)
    mqtt_port = serializers.IntegerField(min_value=1, max_value=65535)
    mqtt_username = serializers.CharField(max_length=255, allow_blank=True)
    mqtt_password = serializers.CharField(max_length=255, allow_blank=True, required=False, write_only=True)
    mqtt_password_set = serializers.BooleanField(read_only=True, required=False)
    mqtt_keepalive = serializers.IntegerField(min_value=5, max_value=3600)
    mqtt_tls = serializers.BooleanField()

    mqtt_reconcile_interval_minutes = serializers.IntegerField(min_value=1, max_value=1440)
    mqtt_reconcile_window_seconds = serializers.IntegerField(min_value=1, max_value=600)

    heartbeat_retention_days = serializers.IntegerField(min_value=1, max_value=3650)
    heartbeat_cleanup_interval_hours = serializers.IntegerField(min_value=1, max_value=720)

    # days a resolved alert is kept before it is deleted
    alert_retention_days = serializers.IntegerField(min_value=1, max_value=3650)

    # hours without a new mqtt report before an error alert is resolved
    alert_stale_hours = serializers.IntegerField(min_value=1, max_value=720)

    # hours an error alert stays visible in the interface
    alert_visible_hours = serializers.IntegerField(min_value=1, max_value=720)

    # days a detection is kept before it is deleted
    detection_retention_days = serializers.IntegerField(min_value=1, max_value=3650)

    # hours a detection stays visible in the interface
    detection_visible_hours = serializers.IntegerField(min_value=1, max_value=720)

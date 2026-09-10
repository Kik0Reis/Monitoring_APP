from rest_framework import serializers


class AppSettingsSerializer(serializers.Serializer):
    """
    Validates the payload for GET/PUT /api/settings/, which reads and
    writes backend/.env directly (see core/env_settings.py and
    core/views.py). mqtt_password is write-only and optional: leaving it
    blank/omitted means "don't change the stored password".
    """

    mqtt_host = serializers.CharField(max_length=255, allow_blank=False)
    mqtt_port = serializers.IntegerField(min_value=1, max_value=65535)
    mqtt_username = serializers.CharField(max_length=255, allow_blank=True)
    mqtt_password = serializers.CharField(
        max_length=255, allow_blank=True, required=False, write_only=True
    )
    mqtt_password_set = serializers.BooleanField(read_only=True, required=False)
    mqtt_keepalive = serializers.IntegerField(min_value=5, max_value=3600)
    mqtt_tls = serializers.BooleanField()

    mqtt_reconcile_interval_minutes = serializers.IntegerField(
        min_value=1, max_value=1440
    )
    mqtt_reconcile_window_seconds = serializers.IntegerField(min_value=1, max_value=600)

    heartbeat_retention_days = serializers.IntegerField(min_value=1, max_value=3650)
    heartbeat_cleanup_interval_hours = serializers.IntegerField(
        min_value=1, max_value=720
    )

    alert_retention_days = serializers.IntegerField(min_value=1, max_value=3650)

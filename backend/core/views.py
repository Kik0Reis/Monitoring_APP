# api to read and change the settings stored in the .env file

from rest_framework.response import Response
from rest_framework.views import APIView

from core.env_settings import read_env, write_env
from core.serializers import AppSettingsSerializer

# maps each api field name to the .env key it is stored in
ENV_KEYS = {
    "mqtt_host": "MQTT_HOST",
    "mqtt_port": "MQTT_PORT",
    "mqtt_username": "MQTT_USERNAME",
    "mqtt_keepalive": "MQTT_KEEPALIVE",
    "mqtt_tls": "MQTT_TLS",
    "mqtt_reconcile_interval_minutes": "MQTT_RECONCILE_INTERVAL_MINUTES",
    "mqtt_reconcile_window_seconds": "MQTT_RECONCILE_WINDOW_SECONDS",
    "heartbeat_retention_days": "HEARTBEAT_RETENTION_DAYS",
    "heartbeat_cleanup_interval_hours": "HEARTBEAT_CLEANUP_INTERVAL_HOURS",
    "alert_retention_days": "ALERT_RETENTION_DAYS",
    "alert_stale_hours": "ALERT_STALE_HOURS",
    "alert_visible_hours": "ALERT_VISIBLE_HOURS",
    "detection_retention_days": "DETECTION_RETENTION_DAYS",
    "detection_visible_hours": "DETECTION_VISIBLE_HOURS",
}

INT_FIELDS = {
    "mqtt_port",
    "mqtt_keepalive",
    "mqtt_reconcile_interval_minutes",
    "mqtt_reconcile_window_seconds",
    "heartbeat_retention_days",
    "heartbeat_cleanup_interval_hours",
    "alert_retention_days",
    "alert_stale_hours",
    "alert_visible_hours",
    "detection_retention_days",
    "detection_visible_hours",
}

BOOL_FIELDS = {"mqtt_tls"}


# reads the .env file and returns it with the api field names and types
def _current_settings() -> dict:
    raw = read_env()
    data = {}

    for field, env_key in ENV_KEYS.items():
        value = raw.get(env_key, "")

        if field in INT_FIELDS:
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = 0
        elif field in BOOL_FIELDS:
            value = str(value).strip().lower() == "true"

        data[field] = value

    # never return the password, only whether one is set
    data["mqtt_password_set"] = bool(raw.get("MQTT_PASSWORD"))

    return data


# GET /api/settings/ returns the settings and PUT /api/settings/ saves them in the .env file
class SettingsView(APIView):
    # returns the current settings
    def get(self, request):
        return Response(_current_settings())

    # validates the new settings and writes them to the .env file
    def put(self, request):
        current = _current_settings()

        payload = dict(request.data)
        # the password and mqtt_password_set are not part of the saved settings used for validation
        password = payload.pop("mqtt_password", None)
        payload.pop("mqtt_password_set", None)

        merged = {**current, **payload}

        serializer = AppSettingsSerializer(data=merged)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updates = {}

        for field, env_key in ENV_KEYS.items():
            value = validated[field]

            if field in BOOL_FIELDS:
                value = "True" if value else "False"

            updates[env_key] = value

        # an empty or missing password keeps the current one
        if password:
            updates["MQTT_PASSWORD"] = password

        write_env(updates)

        return Response(_current_settings())

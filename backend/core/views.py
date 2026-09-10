from rest_framework.response import Response
from rest_framework.views import APIView

from core.env_settings import read_env, write_env
from core.serializers import AppSettingsSerializer

# Maps the API field name to the .env key it reads/writes.
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
}

INT_FIELDS = {
    "mqtt_port",
    "mqtt_keepalive",
    "mqtt_reconcile_interval_minutes",
    "mqtt_reconcile_window_seconds",
    "heartbeat_retention_days",
    "heartbeat_cleanup_interval_hours",
    "alert_retention_days",
}

BOOL_FIELDS = {"mqtt_tls"}


def _current_settings() -> dict:
    """Read backend/.env and shape it into the API's field names/types."""

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

    data["mqtt_username"] = raw.get("MQTT_USERNAME", "")
    # Never return the password itself -- only whether one is set.
    data["mqtt_password_set"] = bool(raw.get("MQTT_PASSWORD"))

    return data


class SettingsView(APIView):
    """
    Reads and writes backend/.env directly (see core/env_settings.py).
    This is the ONLY place this runtime configuration lives -- there is
    no parallel settings table, and the .env file remains the single
    source of truth. Containers read these values at startup, so most
    changes here require restarting the relevant container to apply.

    Endpoint:

        GET /api/settings/
        PUT /api/settings/
    """

    def get(self, request):
        return Response(_current_settings())

    def put(self, request):
        current = _current_settings()

        payload = dict(request.data)
        # Write-only / read-only fields never get merged back into the
        # "current" snapshot used for validation.
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

        # Blank/omitted password means "don't change it".
        if password:
            updates["MQTT_PASSWORD"] = password

        write_env(updates)

        return Response(_current_settings())

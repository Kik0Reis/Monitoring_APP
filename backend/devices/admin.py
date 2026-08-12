from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "mqtt_identifier",
        "location",
        "status",
        "last_seen",
        "active",
        "created_at",
    )

    list_filter = (
        "status",
        "active",
        "location",
    )

    search_fields = (
        "name",
        "serial_number",
        "mqtt_identifier",
    )

    ordering = (
        "name",
    )
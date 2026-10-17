from django.contrib import admin

from .models import Device


# admin page of the devices
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "mqtt_identifier",
        "location",
        "status",
        "last_seen",
        "active",
        "pending_review",
        "created_at",
    )

    list_filter = ("status", "active", "pending_review", "location")

    search_fields = ("name", "serial_number", "mqtt_identifier")

    ordering = ("name",)

from django.contrib import admin

from .models import Camera


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "camera_identifier",
        "channel",
        "device",
        "status",
        "last_seen",
        "active",
        "pending_review",
        "created_at",
    )

    list_filter = (
        "status",
        "active",
        "pending_review",
        "channel",
        "device",
    )

    search_fields = (
        "name",
        "camera_identifier",
        "device__name",
        "device__mqtt_identifier",
    )

    ordering = ("name",)

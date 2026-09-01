from django.contrib import admin

from .models import CameraAlert, DeviceAlert, DeviceHeartbeat


@admin.register(DeviceAlert)
class DeviceAlertAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "alert_type",
        "severity",
        "active",
        "created_at",
        "resolved_at",
    )

    list_filter = (
        "alert_type",
        "severity",
        "active",
    )

    search_fields = (
        "device__name",
        "message",
    )

    ordering = ("-created_at",)


@admin.register(CameraAlert)
class CameraAlertAdmin(admin.ModelAdmin):
    list_display = (
        "camera",
        "alert_type",
        "severity",
        "active",
        "created_at",
        "resolved_at",
    )

    list_filter = (
        "alert_type",
        "severity",
        "active",
    )

    search_fields = (
        "camera__name",
        "message",
    )

    ordering = ("-created_at",)


@admin.register(DeviceHeartbeat)
class DeviceHeartbeatAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "received_at",
        "cpu",
        "memory",
        "storage",
        "temperature",
    )

    list_filter = ("device",)

    ordering = ("-received_at",)

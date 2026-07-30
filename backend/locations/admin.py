from django.contrib import admin

from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "customer",
        "active",
        "created_at",
    )

    list_filter = (
        "customer",
        "active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )
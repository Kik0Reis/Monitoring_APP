from django.contrib import admin

from .models import Location


# admin page of the locations
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "customer", "active", "pending_review", "created_at")

    list_filter = ("customer", "active", "pending_review")

    search_fields = ("name",)

    ordering = ("name",)

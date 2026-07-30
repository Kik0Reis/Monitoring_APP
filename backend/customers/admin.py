from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "active",
        "created_at",
    )

    list_filter = (
        "country",
        "active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )
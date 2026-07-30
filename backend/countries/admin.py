from django.contrib import admin

from .models import Country


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering = (
        "name",
    )
from django.contrib import admin

from .models import Country


# admin page of the countries
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "pending_review", "created_at")

    list_filter = ("pending_review",)

    search_fields = ("name", "code")

    ordering = ("name",)

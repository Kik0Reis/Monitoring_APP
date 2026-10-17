from django.contrib import admin

from .models import Customer


# admin page of the customers
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "active", "pending_review", "created_at")

    list_filter = ("country", "active", "pending_review")

    search_fields = ("name",)

    ordering = ("name",)

from django.contrib import admin

from .models import Broker


@admin.register(Broker)
class BrokersAdmin(admin.ModelAdmin):
    list_filter = ("name", "user", "created_at", "updated_at")
    list_display = ("name", "user", "created_at", "updated_at")
    list_per_page = 15
    date_hierarchy = "created_at"
    search_fields = ("name", "notes")

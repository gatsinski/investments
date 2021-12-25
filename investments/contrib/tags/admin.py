from django.contrib import admin

from .models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_filter = ("name", "author", "created_at", "updated_at")
    list_display = ("name", "author", "created_at", "updated_at")
    list_per_page = 15
    date_hierarchy = "created_at"
    search_fields = ("name",)

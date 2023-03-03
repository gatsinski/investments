from django.contrib import admin

from .models import Currency, ExchangeRate


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_filter = ("nominal", "created_at", "updated_at")
    list_display = ("name", "code", "nominal", "created_at", "updated_at")
    list_per_page = 15
    date_hierarchy = "created_at"
    search_fields = ("name", "nominal")


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_filter = ("currency", "date", "created_at", "updated_at")
    list_display = ("date", "currency", "rate", "created_at", "updated_at")
    list_per_page = 15
    date_hierarchy = "date"
    search_fields = ("currency__name", "currency__code")

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import Bond, Security, Stock


@admin.register(Security)
class SecuritiesAdmin(admin.ModelAdmin):
    search_fields = ("name",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["user"].initial = request.user

        return form

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        if "autocomplete/" in request.path:
            queryset = queryset.filter(user=request.user)

        return queryset, use_distinct


@admin.register(Stock)
class StocksAdmin(SecuritiesAdmin):
    list_filter = ("user", "sector", "created_at", "updated_at")
    list_display = (
        "name",
        "symbol",
        "units",
        "sector",
        "user",
        "created_at",
        "updated_at",
    )
    list_per_page = 50
    ordering = ("name",)
    date_hierarchy = "created_at"
    search_fields = ("name", "symbol" "notes")

    @admin.display(
        ordering="position__security",
        description=_("Units"),
    )
    def units(self, stock):
        return stock.units


@admin.register(Bond)
class BondsAdmin(SecuritiesAdmin):
    list_filter = ("user", "created_at", "updated_at")
    list_display = ("name", "user", "created_at", "updated_at")
    list_per_page = 50
    date_hierarchy = "created_at"
    ordering = ("name",)
    search_fields = ("name", "notes")
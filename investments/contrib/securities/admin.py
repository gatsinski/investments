import json

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, F
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _

from .constants import SECTOR_CHOICES
from .models import Bond, Security, Stock


@admin.register(Security)
class SecuritiesAdmin(admin.ModelAdmin):
    search_fields = ("name",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        try:
            form.base_fields["user"].initial = request.user
        except KeyError:
            pass

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
    search_fields = ("name", "symbol", "notes")

    @admin.display(description=_("Units"))
    def units(self, stock):
        return stock.units

    actions = [
        "get_sectors_by_number_of_companies",
    ]

    @admin.action(description=_("Show sectors grouped by number of companies"))
    def get_sectors_by_number_of_companies(self, request, queryset):
        queryset = (
            queryset.order_by()
            .values("sector")
            .annotate(value=Count("uuid"), label=F("sector"))
        )
        label_map = {key: value for (key, value) in SECTOR_CHOICES}

        return render(
            request,
            "admin/chart.html",
            context={
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "data": json.dumps(list(queryset), cls=DjangoJSONEncoder),
                "label_map": label_map,
                "chart_name": _("Sectors grouped by number of companies"),
                "chart_label": _("Sectors"),
                "chart_type": "pie",
            },
        )


@admin.register(Bond)
class BondsAdmin(SecuritiesAdmin):
    list_filter = ("user", "created_at", "updated_at")
    list_display = ("name", "user", "created_at", "updated_at")
    list_per_page = 50
    date_hierarchy = "created_at"
    ordering = ("name",)
    search_fields = ("name", "notes")

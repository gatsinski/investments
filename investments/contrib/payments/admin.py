import copy
import json

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import CharField, F, Sum, Value
from django.db.models.functions import (Concat, ExtractDay, ExtractMonth,
                                        ExtractQuarter, ExtractYear, TruncDay,
                                        TruncMonth, TruncQuarter, TruncYear)
from django.shortcuts import render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from investments import chart_constants
from investments.contrib.positions.models import Position
from investments.contrib.securities.constants import SECTOR_CHOICES
from investments.contrib.securities.models import Bond
from investments.contrib.tags.models import Tag
from investments.utils.admin import (get_all_days, get_all_months,
                                     get_all_quarters, get_all_years,
                                     get_chart_data, get_color)

from .models import DividendPayment, InterestPayment


def get_custom_titled_filter(title, filter_class):
    class Wrapper(filter_class):
        def __new__(cls, *args, **kwargs):
            instance = filter_class.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper

class BasePaymentsAdmin(admin.ModelAdmin):
    ordering = ("-recorded_on",)
    list_per_page = 100
    date_hierarchy = "recorded_on"
    list_display = (
        "amount",
        "position_link",
        "security_link",
        "position_units",
        "recorded_on",
        "tag_links",
        "user_link",
        "broker_link",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "position__security__user",
        "recorded_on",
        "created_at",
        "updated_at",
        "tags",
        ("position__broker__name", get_custom_titled_filter(_("Brokers"), admin.FieldListFilter)),
        (
            "position__security__name",
            get_custom_titled_filter(_("Securities"), admin.FieldListFilter),
        ),
    )
    search_fields = ("position__security", "position__broker", "notes")
    autocomplete_fields = ("position",)
    actions = [
        "show_daily_payments",
        "show_daily_payments_with_securities",
        "show_monthly_payments",
        "show_monthly_payments_with_securities",
        "show_quarterly_payments",
        "show_quarterly_payments_with_securities",
        "show_yearly_payments",
        "show_yearly_payments_with_securities",
        "show_securities_by_received_amount",
    ]

    @admin.display(
        ordering="position",
        description=_("Position"),
    )
    def position_link(self, payment):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:positions_position_change", args=(payment.position.pk,)),
                payment.position,
            )
        )

    @admin.display(
        ordering="position__units",
        description=_("Units"),
    )
    def position_units(self, payment):
        return payment.position.units.normalize()

    @admin.display(
        ordering="position__security",
        description=_("Security"),
    )
    def security_link(self, payment):
        security = payment.position.security

        try:
            if security.bond:
                reverse_string = "admin:securities_bond_change"
        except Bond.DoesNotExist:
            reverse_string = "admin:securities_stock_change"

        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse(reverse_string, args=(security.pk,)), security
            )
        )

    @admin.display(
        description=_("Tags"),
    )
    def tag_links(self, payment):
        tag_links = [
            '<a href="{}">{}</a>'.format(
                reverse("admin:tags_tag_change", args=(tag.pk,)),
                tag,
            )
            for tag in payment.tags.all()
        ]

        return mark_safe(" ".join(tag_links))

    @admin.display(
        ordering="user",
        description=_("User"),
    )
    def user_link(self, payment):
        user = payment.position.security.user

        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:users_user_change", args=(user.pk,)),
                user.email,
            )
        )

    @admin.display(
        ordering="position__broker",
        description=_("Broker"),
    )
    def broker_link(self, payment):
        broker = payment.position.broker

        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:brokers_broker_change", args=(broker.pk,)),
                broker,
            )
        )

    @admin.action(description=_("Show payments grouped by days"))
    def show_daily_payments(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                day=ExtractDay("recorded_on"),
                month=ExtractMonth("recorded_on"),
                year=ExtractYear("recorded_on"),
            )
            .values("day", "month", "year")
            .annotate(
                value=Sum("amount"),
                label=Concat(
                    "day",
                    Value("."),
                    "month",
                    Value("."),
                    "year",
                    output_field=CharField(),
                ),
            )
            .order_by(TruncDay("recorded_on"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Payments"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_payments(
            request,
            data=chart_data,
            chart_name=_("Payments grouped by days"),
        )

    @admin.action(description=_("Show payments grouped by days with securities"))
    def show_daily_payments_with_securities(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                day=ExtractDay("recorded_on"),
                month=ExtractMonth("recorded_on"),
                year=ExtractYear("recorded_on"),
                security=F("position__security__name"),
            )
            .values("day", "month", "year", "security")
            .annotate(
                value=Sum("amount"),
                label=Concat(
                    "day",
                    Value("."),
                    "month",
                    Value("."),
                    "year",
                    output_field=CharField(),
                ),
            )
            .order_by(TruncDay("recorded_on"))
        )

        days = get_all_days(queryset)

        results = {
            row["security"]: {"label": row["security"], "data": copy.copy(days)}
            for row in queryset
        }

        for row in queryset:
            security = row["security"]
            label = row["label"]
            results[security]["data"][label] = row["value"]

        datasets = [
            {
                "label": result["label"],
                "data": list(result["data"].values()),
                "backgroundColor": get_color(index),
            }
            for index, result in enumerate(results.values())
        ]

        return self.show_payments(
            request,
            data={"labels": list(days.keys()), "datasets": datasets},
            chart_name=_("Payments grouped by days"),
            chart_config={"is_stacked": True},
        )

    @admin.action(description=_("Show payments grouped by months"))
    def show_monthly_payments(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                month=ExtractMonth("recorded_on"), year=ExtractYear("recorded_on")
            )
            .values("month", "year")
            .annotate(
                value=Sum("amount"),
                label=Concat("month", Value("."), "year", output_field=CharField()),
            )
            .order_by(TruncMonth("recorded_on"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Payments"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_payments(
            request,
            data=chart_data,
            chart_name=_("Payments grouped by months"),
        )

    @admin.action(description=_("Show payments grouped by months with securities"))
    def show_monthly_payments_with_securities(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                month=ExtractMonth("recorded_on"),
                year=ExtractYear("recorded_on"),
                security=F("position__security__name"),
            )
            .values("month", "year", "security")
            .annotate(
                value=Sum("amount"),
                label=Concat("month", Value("."), "year", output_field=CharField()),
            )
            .order_by(TruncMonth("recorded_on"))
        )

        months = get_all_months(queryset)

        results = {
            row["security"]: {"label": row["security"], "data": copy.copy(months)}
            for row in queryset
        }

        for row in queryset:
            security = row["security"]
            label = row["label"]
            results[security]["data"][label] = row["value"]

        datasets = [
            {
                "label": result["label"],
                "data": list(result["data"].values()),
                "backgroundColor": get_color(index),
            }
            for index, result in enumerate(results.values())
        ]

        return self.show_payments(
            request,
            data={"labels": list(months.keys()), "datasets": datasets},
            chart_name=_("Payments grouped by months"),
            chart_config={"is_stacked": True},
        )

    @admin.action(description=_("Show payments grouped by quarters"))
    def show_quarterly_payments(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                quarter=ExtractQuarter("recorded_on"), year=ExtractYear("recorded_on")
            )
            .values("quarter", "year")
            .annotate(
                value=Sum("amount"),
                label=Concat("quarter", Value("/"), "year", output_field=CharField()),
            )
            .order_by(TruncQuarter("recorded_on"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Payments"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_payments(
            request,
            data=chart_data,
            chart_name=_("Payments grouped by quarters"),
        )

    @admin.action(description=_("Show payments grouped by quarters with securities"))
    def show_quarterly_payments_with_securities(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                quarter=ExtractQuarter("recorded_on"),
                year=ExtractYear("recorded_on"),
                security=F("position__security__name"),
            )
            .values("quarter", "year", "security")
            .annotate(
                value=Sum("amount"),
                label=Concat("quarter", Value("/"), "year", output_field=CharField()),
            )
            .order_by(TruncQuarter("recorded_on"))
        )

        quarters = get_all_quarters(queryset)

        results = {
            row["security"]: {"label": row["security"], "data": copy.copy(quarters)}
            for row in queryset
        }

        for row in queryset:
            security = row["security"]
            label = row["label"]
            results[security]["data"][label] = row["value"]

        datasets = [
            {
                "label": result["label"],
                "data": list(result["data"].values()),
                "backgroundColor": get_color(index),
            }
            for index, result in enumerate(results.values())
        ]

        return self.show_payments(
            request,
            data={"labels": list(quarters.keys()), "datasets": datasets},
            chart_name=_("Payments grouped by quarters"),
            chart_config={"is_stacked": True},
        )

    @admin.action(description=_("Show payments grouped by years"))
    def show_yearly_payments(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(year=ExtractYear("recorded_on"))
            .values("year")
            .annotate(
                value=Sum("amount"),
                label=F("year"),
            )
            .order_by(TruncYear("recorded_on"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Payments"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_payments(
            request,
            data=chart_data,
            chart_name=_("Payments grouped by years"),
        )

    @admin.action(description=_("Show payments grouped by years with securities"))
    def show_yearly_payments_with_securities(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                year=ExtractYear("recorded_on"),
                security=F("position__security__name"),
            )
            .values("year", "security")
            .annotate(
                value=Sum("amount"),
                label=F("year"),
            )
            .order_by(TruncYear("recorded_on"))
        )

        years = get_all_years(queryset)

        results = {
            row["security"]: {"label": row["security"], "data": copy.copy(years)}
            for row in queryset
        }

        for row in queryset:
            security = row["security"]
            label = row["label"]
            results[security]["data"][label] = row["value"]

        datasets = [
            {
                "label": result["label"],
                "data": list(result["data"].values()),
                "backgroundColor": get_color(index),
            }
            for index, result in enumerate(results.values())
        ]

        return self.show_payments(
            request,
            data={"labels": list(years.keys()), "datasets": datasets},
            chart_name=_("Payments grouped by years"),
            chart_config={"is_stacked": True},
        )

    @admin.action(description=_("Show securities grouped by received amount"))
    def show_securities_by_received_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .values("position__security__name")
            .annotate(value=Sum("amount"), label=F("position__security__name"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Received amount"),
            colors=chart_constants.COLORS,
        )

        return self.show_payments(
            request,
            data=chart_data,
            chart_name=_("Securities grouped by received amount"),
            chart_type=chart_constants.PIE_CHART,
        )

    def show_payments(
        self,
        request,
        data,
        chart_name,
        chart_type=chart_constants.BAR_CHART,
        chart_config=None,
    ):
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "data": json.dumps(
                data,
                cls=DjangoJSONEncoder,
            ),
            "chart_name": chart_name,
            "chart_type": chart_type,
        }

        if chart_config:
            context["chart_config"] = chart_config

        return render(
            request,
            "admin/chart.html",
            context=context,
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "position",
                "position__broker",
                "position__security",
                "position__security__user",
                "position__security__bond",
                "position__security__stock",
            )
            .prefetch_related(
                "tags",
            )
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        form.base_fields["position"].queryset = Position.objects.filter(
            security__user=request.user
        )
        form.base_fields["tags"].queryset = Tag.objects.filter(author=request.user)

        return form


@admin.register(DividendPayment)
class DividendPaymentsAdmin(BasePaymentsAdmin):
    def __init__(self, model, admin_site):
        self.actions.append("show_sectors_by_received_amount")
        super().__init__(model, admin_site)

    def get_list_display(self, request):
        list_display = list(self.list_display)

        list_display.insert(1, "type")

        return list_display

    def get_list_filter(self, request):
        list_filter = list(self.list_filter)

        list_filter.insert(1, "type")

        return list_filter

    @admin.action(description=_("Show sectors grouped by received amount"))
    def show_sectors_by_received_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .values("position__security__stock__sector")
            .annotate(value=Sum("amount"), label=F("position__security__stock__sector"))
        )

        label_map = {key: value for (key, value) in SECTOR_CHOICES}

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Received amount"),
            colors=chart_constants.COLORS,
            label_map=label_map,
        )

        return self.show_payments(
            request,
            data=chart_data,
            chart_name=_("Sectors grouped by received amount"),
            chart_type=chart_constants.PIE_CHART,
        )


@admin.register(InterestPayment)
class InterestPaymentsAdmin(BasePaymentsAdmin):
    pass

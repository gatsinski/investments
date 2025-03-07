import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin import helpers
from django.core.checks import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg, Case, CharField, Count, F, Sum, Value, When
from django.db.models.functions import (
    Concat,
    ExtractDay,
    ExtractMonth,
    ExtractQuarter,
    ExtractYear,
    TruncDay,
    TruncMonth,
    TruncQuarter,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_object_actions import DjangoObjectActions

from investments import chart_constants
from investments.contrib.currencies.models import ExchangeRate
from investments.contrib.securities.constants import SECTOR_CHOICES
from investments.contrib.securities.models import Bond, Security
from investments.utils.admin import get_chart_data

from .admin_filters import StatusFilter
from .forms import ClosePositionForm
from .models import Position


def custom_titled_filter(title, filter_class):
    class Wrapper(filter_class):
        def __new__(cls, *args, **kwargs):
            instance = filter_class.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


@admin.register(Position)
class PositionsAdmin(DjangoObjectActions, admin.ModelAdmin):
    change_form_template = "admin/positions/change_form.html"
    list_filter = (
        "security__user",
        "opened_at",
        "closed_at",
        ("closed_at", StatusFilter),
        "security__stock__sector",
        (
            "security__name",
            custom_titled_filter(_("Securities"), admin.FieldListFilter),
        ),
    )
    list_display = (
        "position_id",
        "security_link",
        "sector",
        "normalized_units",
        "opened_at",
        "normalized_open_price",
        "open_amount",
        "closed_at",
        "normalized_close_price",
        "close_amount",
        "profit_or_loss",
        "user_link",
    )

    list_per_page = 100
    ordering = ("-opened_at",)
    date_hierarchy = "opened_at"
    search_fields = (
        "position_id",
        "notes",
        "security__name",
        "security__stock__symbol",
    )
    autocomplete_fields = ("security",)
    actions = [
        "show_daily_invested_amount",
        "show_monthly_invested_amount",
        "show_quarterly_invested_amount",
        "show_daily_closed_amount",
        "show_monthly_closed_amount",
        "show_quarterly_closed_amount",
        "show_daily_opened_positions",
        "show_monthly_opened_positions",
        "show_quarterly_opened_positions",
        "show_daily_closed_positions",
        "show_monthly_closed_positions",
        "show_quarterly_closed_positions",
        "show_securities_by_invested_amount",
        "show_sectors_by_invested_amount",
        "show_aggregated_report",
        "show_local_currency_position_report",
        "show_position_report",
        "show_tax_report",
    ]
    change_actions = ("close_position", "open_position")

    @admin.display(
        ordering="security",
        description=_("Security"),
    )
    def security_link(self, position):
        try:
            if position.security.bond:
                reverse_string = "admin:securities_bond_change"
        except Bond.DoesNotExist:
            reverse_string = "admin:securities_stock_change"

        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse(reverse_string, args=(position.security.pk,)), position.security
            )
        )

    @admin.display(
        ordering="security__stock__sector",
        description=_("Sector"),
    )
    def sector(self, position):
        return position.security.stock.get_sector_display()

    @admin.display(
        ordering="units",
        description=_("Units"),
    )
    def normalized_units(self, position):
        return position.units.normalize()

    @admin.display(
        ordering="open_price",
        description=_("Open price"),
    )
    def normalized_open_price(self, position):
        return position.open_price.normalize()

    @admin.display(
        ordering="close_price",
        description=_("Close price"),
    )
    def normalized_close_price(self, position):
        return position.close_price.normalize() if position.close_price else None

    @admin.display(
        ordering=F("open_price") * F("units"),
        description=_("Open amount"),
    )
    def open_amount(self, position):
        return position.open_amount

    @admin.display(
        ordering=F("close_price") * F("units"),
        description=_("Close amount"),
    )
    def close_amount(self, position):
        return position.close_amount

    @admin.display(
        ordering=F("close_price") * F("units") - F("open_price") * F("units"),
        description=_("P/L"),
    )
    def profit_or_loss(self, position):
        return position.profit_or_loss

    @admin.display(
        ordering="security__user",
        description=_("User"),
    )
    def user_link(self, position):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:users_user_change", args=(position.security.user.pk,)),
                position.security.user.email,
            )
        )

    def get_change_actions(self, request, position_id, form_url):
        actions = list(super().get_change_actions(request, position_id, form_url))
        position = self.model.objects.get(pk=position_id)

        if position.is_closed:
            actions.remove("close_position")
        else:
            actions.remove("open_position")

        return actions

    @admin.action(description=_("Show invested amount grouped by days"))
    def show_daily_invested_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                day=ExtractDay("opened_at"),
                month=ExtractMonth("opened_at"),
                year=ExtractYear("opened_at"),
            )
            .values("day", "month", "year")
            .annotate(
                value=Sum(F("open_price") * F("units")),
                label=Concat(
                    "day",
                    Value("."),
                    "month",
                    Value("."),
                    "year",
                    output_field=CharField(),
                ),
            )
            .order_by(TruncDay("opened_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Invested amount"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Invested amount grouped by days"),
        )

    @admin.action(description=_("Show invested amount grouped by months"))
    def show_monthly_invested_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(month=ExtractMonth("opened_at"), year=ExtractYear("opened_at"))
            .values("month", "year")
            .annotate(
                value=Sum(F("open_price") * F("units")),
                label=Concat("month", Value("."), "year", output_field=CharField()),
            )
            .order_by(TruncMonth("opened_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Invested amount"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Invested amount grouped by months"),
        )

    @admin.action(description=_("Show invested amount grouped by quarters"))
    def show_quarterly_invested_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                quarter=ExtractQuarter("opened_at"), year=ExtractYear("opened_at")
            )
            .values("quarter", "year")
            .annotate(
                value=Sum(F("open_price") * F("units")),
                label=Concat("quarter", Value("/"), "year", output_field=CharField()),
            )
            .order_by(TruncQuarter("opened_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Invested amount"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Invested amount grouped by quarters"),
        )

    @admin.action(description=_("Show closed amount grouped by days"))
    def show_daily_closed_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                day=ExtractDay("closed_at"),
                month=ExtractMonth("closed_at"),
                year=ExtractYear("closed_at"),
            )
            .values("day", "month", "year")
            .annotate(
                value=Sum(F("close_price") * F("units")),
                label=Concat(
                    "day",
                    Value("."),
                    "month",
                    Value("."),
                    "year",
                    output_field=CharField(),
                ),
            )
            .order_by(TruncDay("closed_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Closed amount"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Closed amount grouped by days"),
        )

    @admin.action(description=_("Show closed amount grouped by months"))
    def show_monthly_closed_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(month=ExtractMonth("closed_at"), year=ExtractYear("closed_at"))
            .values("month", "year")
            .annotate(
                value=Sum(F("close_price") * F("units")),
                label=Concat("month", Value("."), "year", output_field=CharField()),
            )
            .order_by(TruncMonth("closed_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Closed amount"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Closed amount grouped by months"),
        )

    @admin.action(description=_("Show closed amount grouped by quarters"))
    def show_quarterly_closed_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                quarter=ExtractQuarter("closed_at"), year=ExtractYear("closed_at")
            )
            .values("quarter", "year")
            .annotate(
                value=Sum(F("close_price") * F("units")),
                label=Concat("quarter", Value("/"), "year", output_field=CharField()),
            )
            .order_by(TruncQuarter("closed_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Closed amount"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Closed amount grouped by quarters"),
        )

    @admin.action(description=_("Show opened positions grouped by days"))
    def show_daily_opened_positions(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                day=ExtractDay("opened_at"),
                month=ExtractMonth("opened_at"),
                year=ExtractYear("opened_at"),
            )
            .values("day", "month", "year")
            .annotate(
                value=Count("uuid"),
                label=Concat(
                    "day",
                    Value("."),
                    "month",
                    Value("."),
                    "year",
                    output_field=CharField(),
                ),
            )
            .order_by(TruncDay("opened_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Opened positions"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Opened positions grouped by days"),
        )

    @admin.action(description=_("Show opened positions grouped by months"))
    def show_monthly_opened_positions(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(month=ExtractMonth("opened_at"), year=ExtractYear("opened_at"))
            .values("month", "year")
            .annotate(
                value=Count("uuid"),
                label=Concat("month", Value("."), "year", output_field=CharField()),
            )
            .order_by(TruncMonth("opened_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Opened positions"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Opened positions grouped by months"),
        )

    @admin.action(description=_("Show opened positions grouped by quarters"))
    def show_quarterly_opened_positions(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                quarter=ExtractQuarter("opened_at"), year=ExtractYear("opened_at")
            )
            .values("quarter", "year")
            .annotate(
                value=Count("uuid"),
                label=Concat("quarter", Value("/"), "year", output_field=CharField()),
            )
            .order_by(TruncQuarter("opened_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Opened positions"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Opened positions grouped by quarters"),
        )

    @admin.action(description=_("Show closed positions grouped by days"))
    def show_daily_closed_positions(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                day=ExtractDay("closed_at"),
                month=ExtractMonth("closed_at"),
                year=ExtractYear("closed_at"),
            )
            .values("day", "month", "year")
            .annotate(
                value=Count("uuid"),
                label=Concat(
                    "day",
                    Value("."),
                    "month",
                    Value("."),
                    "year",
                    output_field=CharField(),
                ),
            )
            .order_by(TruncDay("closed_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Closed positions"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Closed positions grouped by days"),
        )

    @admin.action(description=_("Show closed positions grouped by months"))
    def show_monthly_closed_positions(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(month=ExtractMonth("closed_at"), year=ExtractYear("closed_at"))
            .values("month", "year")
            .annotate(
                value=Count("uuid"),
                label=Concat("month", Value("."), "year", output_field=CharField()),
            )
            .order_by(TruncMonth("closed_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Closed positions"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Closed positions grouped by months"),
        )

    @admin.action(description=_("Show closed positions grouped by quarters"))
    def show_quarterly_closed_positions(self, request, queryset):
        queryset = (
            queryset.order_by()
            .annotate(
                quarter=ExtractQuarter("closed_at"), year=ExtractYear("closed_at")
            )
            .values("quarter", "year")
            .annotate(
                value=Count("uuid"),
                label=Concat("quarter", Value("/"), "year", output_field=CharField()),
            )
            .order_by(TruncQuarter("closed_at"))
        )

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Closed positions"),
            colors=[chart_constants.BASE_COLOR],
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Closed positions grouped by quarters"),
        )

    @admin.action(description=_("Show securities grouped by invested amount"))
    def show_securities_by_invested_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .values("security__name")
            .annotate(
                value=Sum(F("open_price") * F("units")), label=F("security__name")
            )
        )

        chart_data = get_chart_data(
            queryset=queryset, label=_("Securities"), colors=chart_constants.COLORS
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Securities grouped by invested amount"),
            chart_type=chart_constants.PIE_CHART,
        )

    @admin.action(description=_("Show sectors grouped by invested amount"))
    def show_sectors_by_invested_amount(self, request, queryset):
        queryset = (
            queryset.order_by()
            .values("security__stock__sector")
            .annotate(
                value=Sum(F("open_price") * F("units")),
                label=F("security__stock__sector"),
            )
        )

        label_map = {key: value for (key, value) in SECTOR_CHOICES}

        chart_data = get_chart_data(
            queryset=queryset,
            label=_("Securities"),
            colors=chart_constants.COLORS,
            label_map=label_map,
        )

        return self.show_positions(
            request,
            data=chart_data,
            chart_name=_("Sectors grouped by invested amount"),
            chart_type=chart_constants.PIE_CHART,
        )

    def show_positions(
        self, request, data, chart_name, chart_type=chart_constants.BAR_CHART
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

        return render(
            request,
            "admin/chart.html",
            context=context,
        )

    @admin.action(description=_("Show aggregated report"))
    def show_aggregated_report(self, request, queryset):
        open_amount = F("open_price") * F("units")
        close_amount = F("close_price") * F("units")

        data = queryset.aggregate(
            open_amount=Sum(open_amount),
            close_amount=Sum(close_amount),
            unrealized_amount=Sum(
                Case(When(close_price__isnull=True, then=open_amount))
            ),
            average_open_price=Avg("open_price"),
            average_close_price=Avg("close_price"),
            position_count=Count("uuid"),
            units_sum=Sum("units"),
            profit_or_loss=(
                Sum(Case(When(close_price__isnull=False, then=close_amount)))
                - Sum(Case(When(close_price__isnull=False, then=open_amount)))
            ),
        )

        exchange_rate = (
            ExchangeRate.objects.filter(currency__code="USD").order_by("date").last()
        )

        return render(
            request,
            "admin/positions/aggregated_report.html",
            context={
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "data": data,
                "exchange_rate": exchange_rate.rate,
            },
        )

    @admin.action(description=_("Show report in BGN"))
    def show_local_currency_position_report(self, request, queryset):
        return self.show_position_report(request, queryset, is_in_local_currency=True)

    @admin.action(description=_("Show tax report"))
    def show_tax_report(self, request, queryset):
        return self.show_position_report(
            request, queryset, is_in_local_currency=True, is_tax_report=True
        )

    @admin.action(description=_("Show report in USD"))
    def show_position_report(
        self, request, queryset, is_in_local_currency=False, is_tax_report=False
    ):
        open_amount = F("open_price") * F("units")
        close_amount = F("close_price") * F("units")

        data = (
            queryset.values("opened_at__date", "closed_at__date", "security__name")
            .annotate(
                open_amount=Sum(open_amount),
                close_amount=Sum(close_amount),
                unrealized_amount=Sum(
                    Case(When(close_price__isnull=True, then=open_amount))
                ),
                profit_or_loss=(
                    Sum(Case(When(close_price__isnull=False, then=close_amount)))
                    - Sum(Case(When(close_price__isnull=False, then=open_amount)))
                ),
                average_open_price=Avg("open_price"),
                average_close_price=Avg("close_price"),
                units=Sum("units"),
                position_count=Count("uuid"),
            )
            .order_by("opened_at__date")
        )

        if is_in_local_currency:
            start_date = data.first()["opened_at__date"]

            last_opened_at_date = data.last()["opened_at__date"]
            last_closed_at_date = data.last()["closed_at__date"]
            end_date = (
                last_opened_at_date
                if not last_closed_at_date or last_opened_at_date > last_closed_at_date
                else last_closed_at_date
            )

            exchange_rates_queryset = ExchangeRate.objects.filter(
                currency__code="USD",
                # In case there is no rate for the start rate.
                # There should be more than 7 days without rates
                date__gte=start_date - timedelta(days=7),
                date__lte=end_date,
            )

            exchange_rates = {
                rate.date.isoformat(): rate for rate in exchange_rates_queryset
            }

            current_date = start_date

            def get_rate(date):
                key = date.isoformat()
                return exchange_rates.get(key)

            while current_date <= end_date:
                exchange_rate = None
                lookout_date = current_date

                exchange_rate = get_rate(lookout_date)

                if exchange_rate:
                    current_date += timedelta(days=1)
                    continue

                while not exchange_rate:
                    # Mooving back in time until we find the rate
                    lookout_date -= timedelta(days=1)
                    exchange_rate = get_rate(lookout_date)

                exchange_rates[current_date.isoformat()] = exchange_rate
                current_date += timedelta(days=1)

        return render(
            request,
            "admin/positions/position_report.html",
            context={
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "data": data,
                "exchange_rates": exchange_rates if is_in_local_currency else None,
                "is_in_local_currency": is_in_local_currency,
                "is_tax_report": is_tax_report,
            },
        )

    def close_position(self, request, position, *args, **kwargs):
        if position.is_closed:
            self.message_user(request, _("The position is already closed"))

            return redirect(
                "admin:positions_position_change", object_id=str(position.pk)
            )

        if "apply" in request.POST:
            form = ClosePositionForm(request.POST)

            if form.is_valid():
                cleaned_data = form.cleaned_data
                position.close_price = cleaned_data.get("close_price")
                position.closed_at = timezone.now()
                position.save()

                self.message_user(request, _("The position was successfully closed"))

                return redirect(
                    "admin:positions_position_change", object_id=str(position.pk)
                )
        else:
            form = ClosePositionForm()

        adminForm = helpers.AdminForm(
            form=form,
            fieldsets=((None, {"fields": ("close_price",)}),),
            prepopulated_fields={},
            readonly_fields=[],
            model_admin=self,
        )

        return render(
            request,
            "admin/positions/close_position_form.html",
            context={
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "adminForm": adminForm,
                "object": position,
            },
        )

    def open_position(self, request, position):
        if position.is_closed:
            position.closed_at = None
            position.close_price = None
            position.save()
            self.message_user(request, _("The position was successfully opened"))
        else:
            self.message_user(
                request, _("The position is already open"), level=messages.WARNING
            )

        return redirect("admin:positions_position_change", object_id=str(position.pk))

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "security",
                "broker",
                "security__user",
                "security__bond",
                "security__stock",
            )
            .prefetch_related(
                "tags",
            )
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        form.base_fields["security"].queryset = Security.objects.filter(
            user=request.user
        )
        form.base_fields["broker"].initial = form.base_fields["broker"].queryset.first()

        return form

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        if "autocomplete/" in request.path:
            queryset = queryset.filter(security__user=request.user)

        return queryset, use_distinct

import pandas

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from django.utils.timezone import make_aware
from decimal import Decimal
from investments.contrib.currencies.models import ExchangeRate
from datetime import timedelta

from .models import Statement


@admin.register(Statement)
class StatementsAdmin(admin.ModelAdmin):
    list_filter = ("user", "created_at", "updated_at")
    list_display = ("uuid", "name", "user", "statement", "created_at", "updated_at")
    list_per_page = 15
    date_hierarchy = "created_at"
    actions = [
        "show_sales_report",
        "show_payment_report",
    ]

    @admin.action(description=_("Show sales report"))
    def show_sales_report(self, request, queryset):
        file = queryset.first().statement
        df = pandas.read_csv(file)

        df = df[df["Action"].isin(["Market sell", "Limit sell"])]

        total_buy_price = 0
        total_sell_price = 0
        profit = 0
        loss = 0

        df["Time"] = pandas.to_datetime(df["Time"])

        start_date = make_aware(df["Time"].min().to_pydatetime()).date()
        end_date = make_aware(df["Time"].max().to_pydatetime()).date()
        exchange_rates_usd = self.get_exchange_rates("USD", start_date, end_date)
        exchange_rate_eur = Decimal("1.95583")

        for index, row in df.iterrows():
            date = row["Time"].to_pydatetime().date()

            # def get_buy_price():
            #     raw = Decimal(str(row["Price / share"]))
            #     currency = row["Currency (Price / share)"]
            #     shares_count = Decimal(str(row["No. of shares"]))
            #     price_per_share = self.get_value_in_eur(
            #         value=raw,
            #         currency=currency,
            #         date=date,
            #         exchange_rates_usd=exchange_rates_usd,
            #         exchange_rate_eur=exchange_rate_eur,
            #     )

            #     return shares_count * price_per_share

            def get_buy_price():
                raw = Decimal(str(row["Total"]))
                currency = row["Currency (Total)"]

                return self.get_value_in_eur(
                    value=raw,
                    currency=currency,
                    date=date,
                    exchange_rates_usd=exchange_rates_usd,
                    exchange_rate_eur=exchange_rate_eur,
                )

            def get_result():
                raw_result = Decimal(str(row["Result"]))
                currency = row["Currency (Result)"]

                return self.get_value_in_eur(
                    value=raw_result,
                    currency=currency,
                    date=date,
                    exchange_rates_usd=exchange_rates_usd,
                    exchange_rate_eur=exchange_rate_eur,
                )

            total_buy_price += get_buy_price()

            result = get_result()

            total_sell_price += get_buy_price() + result

            if result > 0:
                profit += result
            else:
                loss += result

        return render(
            request,
            "admin/reports/sales_report.html",
            context={
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "total_buy_price": total_buy_price,
                "total_sell_price": total_sell_price,
                "profit": profit,
                "loss": loss,
                "result": profit + loss,
                "exchange_rate_eur": exchange_rate_eur,
            },
        )

    @admin.action(description=_("Show payment report"))
    def show_payment_report(self, request, queryset):
        file = queryset.first().statement
        df = pandas.read_csv(file)

        df = df[df["Action"] == "Dividend (Dividend)"]

        processed_data = []

        df["Time"] = pandas.to_datetime(df["Time"])

        start_date = make_aware(df["Time"].min().to_pydatetime()).date()
        end_date = make_aware(df["Time"].max().to_pydatetime()).date()
        exchange_rates_usd = self.get_exchange_rates("USD", start_date, end_date)
        exchange_rate_eur = Decimal("1.95583")

        for index, row in df.iterrows():
            date = row["Time"].to_pydatetime().date()
            received_amount = Decimal(str(row["Total"]))  # EUR

            def get_total():
                raw_result = Decimal(str(row["Result"]))  # EUR or BGN
                currency = row["Currency (Result)"]

                return self.get_value_in_eur(
                    value=raw_result,
                    currency=currency,
                    date=date,
                    exchange_rates_usd=exchange_rates_usd,
                    exchange_rate_eur=exchange_rate_eur,
                )

            currency = row["Currency (Withholding tax)"]
            withholding_tax = Decimal(str(row["Withholding tax"]))

            withheld_tax = self.get_value_in_eur(
                withholding_tax, currency, date, exchange_rates_usd, exchange_rate_eur
            )
            gross_amount = received_amount + withheld_tax  # EUR

            processed_row = {
                "date": date,
                "symbol": row["Ticker"],
                "name": row["Name"],
                "gross_amount": gross_amount,
                "withhold_tax": withheld_tax,
                "tax_to_pay": (
                    0
                    if Decimal(str(row["Withholding tax"]))
                    else Decimal(str(row["Total"])) * Decimal("0.1")
                ),
            }
            processed_data.append(processed_row)

        return render(
            request,
            "admin/reports/payment_report.html",
            context={
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "data": processed_data,
                "exchange_rates_usd": exchange_rates_usd,
                "exchange_rate_eur": exchange_rate_eur,
            },
        )

    def get_value_in_eur(
        self, value, currency, date, exchange_rates_usd, exchange_rate_eur
    ):
        if currency == "EUR":
            return value
        elif currency == "USD":
            us_rate = exchange_rates_usd.get(date.isoformat()).rate
            in_bgn = value * us_rate
            in_eur = in_bgn / exchange_rate_eur
            return in_eur
        elif currency == "BGN":
            return value / exchange_rate_eur

    def get_exchange_rates(self, currency, start_date, end_date):
        exchange_rates_queryset_usd = ExchangeRate.objects.filter(
            currency__code=currency,
            # In case there is no rate for the start rate.
            # There should be more than 7 days without rates
            date__gte=start_date - timedelta(days=7),
            date__lte=end_date,
        )

        exchange_rates = {
            rate.date.isoformat(): rate for rate in exchange_rates_queryset_usd
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

        return exchange_rates

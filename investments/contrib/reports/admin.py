from django.contrib import admin

from .models import Report


@admin.register(Report)
class Reports(admin.ModelAdmin):
    list_filter = ("type", "created_at", "updated_at")
    list_display = ("uuid", "file", "type", "created_at", "updated_at")
    list_per_page = 15
    date_hierarchy = "created_at"
    actions = [
        "show_payment_report",
    ]

  @admin.action(description=_("Show payment report"))
    def show_payment_report(self, request, queryset):
        file = queryset.first().file
        dataFrame = pandas.read_csv(file)

        for index, row in dataFrame.iterrows():
            isBuy = row['Action'] == "Market buy"
            isSell = row['Action'] == "Market sell"

            activity = {
                "date": make_aware(
                    datetime.strptime(row['Time'], "%Y-%m-%d %H:%M:%S.%f")
                ),
                "type": row['Action'],
                "symbol": row['Ticker'],
                "amount": Decimal(str(row['Total'])),
                "units": row['No. of shares'],
                "position_id": row['ID'] if isBuy else '',
                "close_id": row['ID'] if isSell else '',
            }

            


        # data = queryset.values("recorded_on", "position__security").annotate(total_amount=Sum('amount'))
        data = (
            queryset.values("recorded_on", "position__security__name")
            .annotate(
                total_received_amount=Sum("amount"),
                total_withheld_tax=Sum("withheld_tax"),
                gross_amount=Sum("amount") + Sum("withheld_tax"),
            )
            .order_by("recorded_on")
        )

        start_date = data.first()["recorded_on"]
        end_date = data.last()["recorded_on"]

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
            "admin/reports/payment_report.html",
            context={
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "data": data,
                "exchange_rates": exchange_rates,
            },
        )

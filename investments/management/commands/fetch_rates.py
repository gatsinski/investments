import csv
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

import requests
from django.core.management.base import BaseCommand

from investments.contrib.currencies.models import Currency, ExchangeRate


class Command(BaseCommand):
    help = "Fetch exchange rates from the site of BNB"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str)
        parser.add_argument(
            "--create",
            type=bool,
            default=False,
            help="Whether to create a new currency if missing.",
        )

    def handle(self, *args, **options):
        date_input = options.get("date")

        if date_input:
            date = datetime.strptime(date_input, "%d.%m.%Y")
        else:
            self.write_warning("Date not provided. Using today.")
            date = datetime.now()
            date_input = date.strftime("%d.%m.%Y")

        should_create_currency = options.get("create")

        base_url = "https://www.bnb.bg/Statistics/StExternalSector/StExchangeRates/StERForeignCurrencies/index.htm"
        params = {
            "downloadOper": "true",
            "group1": "first",
            "firstDays": str(date.day).zfill(2),
            "firstMonths": str(date.month).zfill(2),
            "firstYear": date.year,
            "search": "true",
            "showChart": "false",
            "showChartButton": "false",
            "type": "CSV",
        }

        url = f"{base_url}?{urlencode(params)}"
        response = requests.get(url)

        if "csv" not in response.headers.get("Content-Type"):
            self.write_error("The response doesn't contain valid CSV/")
            return

        content = response.content.decode("utf-8").splitlines()

        reader = csv.reader(content)

        next(reader, None)
        next(reader, None)

        for row in reader:
            if len(row) < 5:
                continue

            date_column, name, code, nominal, exchange_rate = row[:5]

            if date.date() != datetime.strptime(date_column, "%d.%m.%Y").date():
                self.write_error(
                    f"Response date {date_column} is different than the requested date {date_input}."
                )

            if nominal == "n/a" or exchange_rate == "n/a":
                self.write_warning(
                    f"Found an item for currency {name} ({code}) with nominal {nominal} and exchange rate {exchange_rate}. Skipping."
                )
                continue

            currency = Currency.objects.filter(code=code).first()

            if not currency and should_create_currency:
                currency = Currency.objects.create(
                    name=name, code=code, nominal=int(nominal)
                )
                self.write_success(
                    f"Successfully created currency with name {currency.name}, "
                    f"code {currency.code} and nominal {currency.nominal}."
                )
            elif not currency:
                self.write_error(f"Failed to find currency with code {name}.")
                return

            obj, created = ExchangeRate.objects.get_or_create(
                currency=currency,
                date=date,
                defaults={"rate": Decimal(exchange_rate)},
            )

            if created:
                self.write_success(
                    f"Successfully created exchange rate for currency {currency.code} with rate {exchange_rate}."
                )
            else:
                self.write_warning(
                    f"Found existing exchange rate record for {currency.code} with date {date}. Skipping."
                )

        self.write_success(f"Successfully imported currency data for {date_input}")

    def write_success(self, message):
        self.stdout.write(self.style.SUCCESS(message))

    def write_warning(self, message):
        self.stdout.write(self.style.WARNING(message))

    def write_error(self, message):
        self.stdout.write(self.style.ERROR(message))

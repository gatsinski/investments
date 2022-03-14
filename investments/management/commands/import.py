import openpyxl
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware


from investments.contrib.securities.models import Stock
from investments.contrib.securities import constants
from investments.contrib.positions.models import Position
from investments.contrib.payments.models import DividendPayment
from investments.contrib.brokers.models import Broker
from investments.contrib.tags.models import Tag

UserModel = get_user_model()


class Command(BaseCommand):
    help = "Imports investment data from xls"

    def add_arguments(self, parser):
        parser.add_argument("file", nargs="+", type=str)

    def handle(self, *args, **options):
        filename = options.get("file")[0]

        workbook = openpyxl.load_workbook(
            filename=filename, read_only=True, data_only=True
        )

        worksheet = workbook["Dividends"]

        for row in worksheet.iter_rows(min_row=2):
            date = row[0]
            aware_date = make_aware(datetime.strptime(date.value, '%d/%m/%Y %H:%M:%S'))

            name = row[1]
            received_dividend = row[2]
            position_id = row[5]

            position = Position.objects.filter(position_id=position_id.value).first()

            if not position:

                self.stdout.write(self.style.ERROR(f"Failed to find {position_id.value}. Skipping"))
                continue

            payment, created = DividendPayment.objects.get_or_create(
                position=position,
                amount=received_dividend.value,
                recorded_on=aware_date,
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Successfully created payment for {position.uuid} ({position.security.name}) with id {payment.uuid}."))
            else:
                self.stdout.write(self.style.WARNING(f"Found existing payment for {position.uuid} ({position.security.name}) with id {payment.uuid}"))

        workbook.close()

        self.stdout.write(self.style.SUCCESS("Successfully imported all data"))

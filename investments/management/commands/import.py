from datetime import datetime

import openpyxl
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from investments.contrib.payments.models import DividendPayment
from investments.contrib.positions.models import Position

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
            aware_date = make_aware(datetime.strptime(date.value, "%d/%m/%Y %H:%M:%S"))

            received_dividend = row[2]
            position_id = row[5]

            position = Position.objects.filter(position_id=position_id.value).first()

            if not position:
                self.stdout.write(
                    self.style.ERROR(f"Failed to find {position_id.value}. Skipping.")
                )
                continue

            payment, created = DividendPayment.objects.get_or_create(
                position=position,
                amount=received_dividend.value,
                recorded_on=aware_date,
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully created payment for {position.position_id} ({position.security.name}) "
                        f"with received amount {payment.amount} recorded on {payment.recorded_on} with id {payment.uuid}."
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Found existing payment for {position.uuid} ({position.security.name}) with id {payment.uuid}"
                    )
                )

        workbook.close()

        self.stdout.write(self.style.SUCCESS("Successfully imported all data"))

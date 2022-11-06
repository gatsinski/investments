from datetime import datetime

import openpyxl
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from investments.contrib.brokers.models import Broker
from investments.contrib.payments.models import DividendPayment
from investments.contrib.positions.models import Position
from investments.contrib.securities.models import Stock

UserModel = get_user_model()


class Command(BaseCommand):
    help = "Imports investment data from xls"

    def add_arguments(self, parser):
        parser.add_argument("file", nargs=1, type=str)
        parser.add_argument("user", nargs="?", type=str)
        parser.add_argument("broker", nargs="?", type=str)

    def handle(self, *args, **options):
        filename = options.get("file")[0]

        user_email = options.get("user")
        user = self.get_user(user_email)

        if not user:
            return

        broker_name = options.get("broker")
        broker = self.get_broker(broker_name, user)

        if not broker:
            return

        workbook = openpyxl.load_workbook(
            filename=filename, read_only=True, data_only=True
        )

        self.handle_positions(workbook, user, broker)
        self.handle_dividends(workbook)

        workbook.close()

        self.stdout.write(self.style.SUCCESS("Successfully imported all data"))

    def get_user(self, user_email):
        if user_email:
            user = UserModel.objects.filter(email=user_email).first()

            if user:
                return user

            self.stdout.write(
                self.style.ERROR(f"Unable to find the user with email {user_email}.")
            )
        else:
            self.stdout.write(
                self.style.WARNING("No user provided. Using the first available user.")
            )

            user = UserModel.objects.last()

            if user:
                return user

            self.stdout.write(self.style.ERROR("Unable to find user."))

    def get_broker(self, broker_name, user):
        if broker_name:
            broker = Broker.objects.filter(user=user, name=broker_name).first()

            if broker:
                return broker

            self.stdout.write(
                self.style.ERROR(f"Unable to find broker with name {broker_name}.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"No broker provided. Using the first broker belonging to {user.email}."
                )
            )

            broker = Broker.objects.filter(user=user).first()

            if broker:
                return broker

            self.stdout.write(
                self.style.ERROR(
                    f"Unable to find any broker belonging to {user.email}."
                )
            )

    def handle_dividends(self, workbook):
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

    def handle_positions(self, workbook, user, broker):
        worksheet = workbook["Account Activity"]

        for row in worksheet.iter_rows(min_row=2):
            date = row[0]
            aware_date = make_aware(datetime.strptime(date.value, "%d/%m/%Y %H:%M:%S"))

            position_id = row[8].value
            activity_type = row[1].value
            raw_symbol = row[2].value
            amount = row[3].value
            units = row[4].value
            asset_type = row[9].value

            if not position_id:
                continue

            position = Position.objects.filter(position_id=position_id).first()

            if position:
                self.stdout.write(
                    self.style.WARNING(
                        f"Position {position_id} already exists. Skipping"
                    )
                )
                continue

            if activity_type != "Open Position":
                continue

            if asset_type != "Stocks":
                self.stdout.write(
                    self.style.WARNING(
                        f"Encountered an asset of type {asset_type}. Skipping"
                    )
                )
                continue

            symbol = raw_symbol.split("/")[0]

            stock = Stock.objects.filter(symbol=symbol, user=user).first()

            if not stock:
                stock = Stock.objects.filter(
                    aliases__contains=symbol, user=user
                ).first()

            if not stock:
                self.stdout.write(
                    self.style.ERROR(
                        f"Unable to find stock with symbol {symbol} belonging to user {user.email}. Skipping"
                    )
                )
                continue

            position = Position.objects.create(
                position_id=position_id,
                units=units,
                open_price=amount / float(units),
                security=stock,
                broker=broker,
                opened_at=aware_date,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created position with id {position.position_id} - Buy { position.units } {position.security.name} at {position.open_price}"
                )
            )

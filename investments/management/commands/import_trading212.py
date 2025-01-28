import re
from datetime import datetime
from decimal import Decimal

import pandas
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
    help = "Imports investment data from csv"

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

        # Read CSV file into a DataFrame
        dataFrame = pandas.read_csv(filename)

        self.handle_positions(dataFrame, user, broker)
        self.handle_dividends(dataFrame)

        self.write_success("Successfully imported all data")

    def get_user(self, user_email):
        if user_email:
            user = UserModel.objects.filter(email=user_email).first()

            if user:
                return user

            self.write_error(f"Unable to find the user with email {user_email}.")
        else:
            self.write_warning("No user provided. Using the first available user.")

            user = UserModel.objects.last()

            if user:
                return user

            self.write_error("Unable to find user.")

    def get_broker(self, broker_name, user):
        if broker_name:
            broker = Broker.objects.filter(user=user, name=broker_name).first()

            if broker:
                return broker

            self.write_error(f"Unable to find broker with name {broker_name}.")
        else:
            self.write_warning(
                f"No broker provided. Using the first broker belonging to {user.email}."
            )

            broker = Broker.objects.filter(user=user).first()

            if broker:
                return broker

            self.write_error(f"Unable to find any broker belonging to {user.email}.")

    def handle_dividends(self, workbook):
        for index, row in dataFrame.iterrows():
            if row['Action'] != "Dividend (Dividend)":
                continue

            date = row['Time']
            aware_date = make_aware(datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f"))

            received_dividend = row['Total']
            withheld_tax = Decimal(str(row['Withholding tax']))
            withheld_tax_rate = withheld_tax / received_dividend * 100

            position_id = row['ID']

            position = Position.objects.filter(position_id=position_id).first()

            if not position:
                self.write_error(f"Failed to find {position_id}. Skipping.")
                continue

            payment, created = DividendPayment.objects.get_or_create(
                position=position,
                amount=received_dividend.value,
                recorded_on=aware_date,
                defaults={
                    "withheld_tax": withheld_tax,
                    "withheld_tax_rate": withheld_tax_rate,
                },
            )

            if created:
                self.write_success(
                    f"Successfully created payment for {position.position_id} ({position.security.name}) "
                    f"with received amount {payment.amount} recorded on {payment.recorded_on} with id {payment.uuid}."
                )
            else:
                self.write_warning(
                    f"Found existing payment for {position.position_id} ({position.security.name}) with id {payment.uuid}"
                )

                if not payment.withheld_tax or not payment.withheld_tax_rate:
                    payment.withheld_tax = withheld_tax
                    payment.withheld_tax_rate = withheld_tax_rate
                    payment.save(update_fields=("withheld_tax", "withheld_tax_rate"))

                    self.write_success(
                        f"The existing payment for {position.position_id} ({position.security.name}) with id {payment.uuid} "
                        f"had no tax data. It was successfully updated with witheld tax {withheld_tax} and rate {withheld_tax_rate}%."
                    )

    def handle_positions(self, dataFrame, user, broker):

        for index, row in dataFrame.iterrows():
            isBuy = row['Action'] == "Market buy"
            isSell = row['Action'] == "Market sell"

            if not isBuy and not isSell:
                continue

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

            if not activity["position_id"]:
                continue

            if activity["type"] == "Market buy":
                position = Position.objects.filter(
                    position_id=activity["position_id"]
                ).first()

                self.handle_opened_positions(activity, position, user, broker)
            elif activity["type"] == "Market sell":
                self.handle_closed_positions(activity, user, broker)

    def handle_opened_positions(self, activity, position, user, broker):
        if position:
            self.write_warning(
                f"Position {position.position_id} already exists. Skipping"
            )
            return

        stock = Stock.objects.filter(symbol=activity["symbol"], user=user).first()

        if not stock:
            stock = Stock.objects.filter(
                aliases__contains=activity["symbol"], user=user
            ).first()

        if not stock:
            self.write_error(
                f"Unable to find stock with symbol {activity['symbol']} belonging to user {user.email}. Skipping"
            )
            return

        for i in range(activity["units"]):  # handle partials
            position = Position.objects.create(
                position_id=activity["position_id"],
                units=1,
                open_price=activity["amount"] / Decimal(activity["units"]),
                security=stock,
                broker=broker,
                opened_at=activity["date"],
            )

            self.write_success(
                f"Successfully created position with id {position.position_id} - Buy {position.units} {position.security.name} at {position.open_price}"
            )

    def handle_closed_positions(self, activity, user, broker):
        closed_positions = Position.objects.filter(
            security__stock__symbol=activity["symbol"],
            close_id=activity['close_id'],
        ).count()

        units = activity["units"]

        if closed_positions == units:
            self.write_error(
                f"{closed_positions} units of {activity["symbol"]} are already closed. Skipping."
            )
            return
        elif closed_positions < units:
            remaining_to_close = units - closed_positions
            self.write_warning(
                f"{closed_positions} units of {activity["symbol"]} are already closed but there are {remaining_to_close} more."
            )

            positions_to_close = Position.objects.filter(
                security__stock__symbol=activity["symbol"],
                close_id=activity['close_id'],
                broker=broker
            )[:remaining_to_close]

            for position in positions_to_close:
                position.close_price = position.open_price + activity["amount"] / Decimal(units) # TODO: Check if this is correct
                position.closed_at = activity["date"]
                position.close_id = activity["close_id"]

                position.save(update_fields=["close_price", "closed_at", "close_id"])

                self.write_success(
                    f"Successfully closed position with id {position.position_id} - {position.units} {position.security.name} at {position.close_price}"
                )

    def write_success(self, message):
        self.stdout.write(self.style.SUCCESS(message))

    def write_warning(self, message):
        self.stdout.write(self.style.WARNING(message))

    def write_error(self, message):
        self.stdout.write(self.style.ERROR(message))

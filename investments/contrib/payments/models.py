import uuid

from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from investments.models import TimestampedModel

from . import constants

UserModel = get_user_model()


class Payment(TimestampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    recorded_on = models.DateField(_("Recorded on"))
    tags = models.ManyToManyField(
        "tags.Tag",
        related_name="dividend_payments",
        verbose_name=_("Tags"),
        blank=True,
    )

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

    def __str__(self):
        return gettext(f"Payment {self.uuid}")


class DividendPayment(Payment):
    amount = models.DecimalField(
        _("Amount"),
        max_digits=12,
        decimal_places=2,
        validators=[validators.MinValueValidator(0)],
    )
    type = models.CharField(
        _("Type"), max_length=254, choices=constants.DIVIDEND_TYPES, blank=True
    )
    position = models.ForeignKey(
        "positions.Position", related_name="dividend_payments", on_delete=models.CASCADE
    )
    notes = models.CharField(_("Notes"), max_length=1024, blank=True)

    class Meta:
        verbose_name = _("Dividend Payment")
        verbose_name_plural = _("Dividend Payments")

    def __str__(self):
        return gettext(
            f"Dividend Payment, position {self.position.position_id}, {self.position.security}"
        )


class InterestPayment(Payment):
    amount = models.DecimalField(
        _("Amount"),
        max_digits=12,
        decimal_places=2,
        validators=[validators.MinValueValidator(0)],
    )
    position = models.ForeignKey(
        "positions.Position", related_name="interest_payments", on_delete=models.CASCADE
    )
    notes = models.CharField(_("Notes"), max_length=1024, blank=True)

    class Meta:
        verbose_name = _("Interest Payment")
        verbose_name_plural = _("Interest Payments")

    def __str__(self):
        return gettext(
            f"Interest Payment, position {self.position.position_id}, {self.position.security}"
        )

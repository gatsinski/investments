import uuid

from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _

from investments.models import TimestampedModel

UserModel = get_user_model()


class Currency(TimestampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(_("Name"), max_length=254)
    code = models.CharField(_("ISO code"), max_length=3, blank=True, unique=True)
    nominal = models.PositiveSmallIntegerField(_("Nominal"), default=1)

    class Meta:
        verbose_name = _("Currency")
        verbose_name_plural = _("Currencies")

    def __str__(self):
        return f"{self.name} ({self.code})"


class ExchangeRate(TimestampedModel):
    currency = models.ForeignKey(
        Currency, related_name="exchange_rates", on_delete=models.CASCADE
    )
    date = models.DateField(_("Date"))
    rate = models.DecimalField(
        _("Rate"),
        max_digits=15,
        decimal_places=5,
        validators=[validators.MinValueValidator(0)],
    )

    class Meta:
        verbose_name = _("Exchange rate")
        verbose_name_plural = _("Exchange rates")
        unique_together = (("currency", "date"),)

    def __str__(self):
        return f"{self.currency.code} - {self.date} - {self.rate}"

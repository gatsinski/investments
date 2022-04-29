import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from investments.models import TimestampedModel

from . import constants

UserModel = get_user_model()


class Security(TimestampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(_("Name"), max_length=254)
    user = models.ForeignKey(
        UserModel, related_name="securities", on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("Security")
        verbose_name_plural = _("Securities")

    def __str__(self):
        return self.name


class Stock(Security):
    symbol = models.CharField(_("Symbol"), max_length=254)
    sector = models.IntegerField(
        _("Sector"),
        choices=constants.SECTOR_CHOICES,
    )
    type = models.CharField(
        _("Type"),
        max_length=64,
        default=constants.COMMON_STOCK,
        choices=constants.STOCK_TYPE_CHOICES,
    )
    notes = models.CharField(_("Notes"), max_length=1024, blank=True)

    class Meta:
        verbose_name = _("Stock")
        verbose_name_plural = _("Stocks")

    def __str__(self):
        return self.name

    @property
    def units(self):
        return self.positions.filter(closed_at__isnull=True).aggregate(Sum("units"))[
            "units__sum"
        ]


class Bond(Security):
    type = models.CharField(
        _("Type"),
        max_length=64,
        default=constants.GOVERNMENT_BOND,
        choices=constants.BOND_TYPE_CHOICES,
    )
    notes = models.CharField(_("Notes"), max_length=1024, blank=True)

    class Meta:
        verbose_name = _("Bond")
        verbose_name_plural = _("Bonds")

    def __str__(self):
        return self.name

import uuid

from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _

from investments.models import TimestampedModel


class Position(TimestampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    position_id = models.CharField(
        _("ID"),
        max_length=254,
        help_text=_(
            "The unique position ID used to identify this position within broker's platform."
        ),
    )
    units = models.DecimalField(
        _("Units"),
        max_digits=16,
        decimal_places=6,
        validators=[validators.MinValueValidator(0)],
    )
    open_price = models.DecimalField(
        _("Open price"),
        max_digits=16,
        decimal_places=6,
        validators=[validators.MinValueValidator(0)],
    )
    close_price = models.DecimalField(
        _("Close price"),
        max_digits=16,
        decimal_places=6,
        validators=[validators.MinValueValidator(0)],
        blank=True,
        null=True,
    )
    security = models.ForeignKey(
        "securities.Security", related_name="positions", on_delete=models.CASCADE
    )
    broker = models.ForeignKey(
        "brokers.Broker", related_name="positions", on_delete=models.CASCADE
    )
    tags = models.ManyToManyField(
        "tags.Tag", related_name="securities", verbose_name=_("Tags"), blank=True
    )
    opened_at = models.DateTimeField(_("Opened at"))
    closed_at = models.DateTimeField(_("Closed at"), blank=True, null=True)
    close_id = models.CharField(
        _("Close ID"),
        max_length=254,
        blank=True,
        help_text=_(
            "The unique id of the close order used to identify this action within broker's platform."
        ),
    )
    notes = models.CharField(_("Notes"), max_length=1024, blank=True)

    class Meta:
        verbose_name = _("Position")
        verbose_name_plural = _("Positions")
        unique_together = [["position_id", "broker"]]

    def __str__(self):
        return f"{self.position_id} - {self.security.name}"

    @property
    def is_closed(self):
        return self.close_price and self.closed_at is not None

    @property
    def open_amount(self):
        return round(self.units * self.open_price, 2)

    @property
    def close_amount(self):
        return round(self.units * self.close_price, 2) if self.is_closed else None

    @property
    def profit_or_loss(self):
        return self.close_amount - self.open_amount if self.is_closed else None

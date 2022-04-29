import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from investments.models import TimestampedModel

UserModel = get_user_model()


class Broker(TimestampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(_("Name"), max_length=254)
    user = models.ForeignKey(
        UserModel, related_name="brokers", on_delete=models.CASCADE
    )
    notes = models.CharField(_("Notes"), max_length=1024, blank=True)

    class Meta:
        verbose_name = _("Broker")
        verbose_name_plural = _("Brokers")

    def __str__(self):
        return self.name

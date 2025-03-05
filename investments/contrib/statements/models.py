import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from investments.models import TimestampedModel

UserModel = get_user_model()


class Statement(TimestampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(_("Name"), max_length=254)
    user = models.ForeignKey(
        UserModel, related_name="statements", on_delete=models.CASCADE
    )

    statement = models.FileField(verbose_name=_("Statement"))

    class Meta:
        verbose_name = _("Statement")
        verbose_name_plural = _("Statements")

    def __str__(self):
        return f"{self.name}"

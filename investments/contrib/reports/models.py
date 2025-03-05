import uuid

from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _

from investments.models import TimestampedModel

from . import constants

UserModel = get_user_model()


class Report(TimestampedModel):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    file = models.FileField(verbose_name=_("File"))

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")

    def __str__(self):
        return f"{self.file.name}"

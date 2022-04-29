from django.utils.translation import gettext_lazy as _

MOHTLY = "monthly"
QUARTERLY = "quarterly"
SEMIANNUAL = "semiannual"
ANNUAL = "annual"
SPECIAL = "special"

DIVIDEND_TYPES = (
    (MOHTLY, _("Monthly")),
    (QUARTERLY, _("Quarterly")),
    (SEMIANNUAL, _("Semiannual")),
    (ANNUAL, _("Annual")),
    (SPECIAL, _("Special")),
)

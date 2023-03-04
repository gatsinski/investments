from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.simple_tag
def get_local_currency_rate(date, rates):
    rate_instance = rates.get(date.isoformat())

    if not rate_instance:
        return _("No exchange rate found")

    return rate_instance.rate


@register.filter
def to_local_currency(value, rate):
    return value * rate if rate and value else None

from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.simple_tag
def get_local_currency_rate(date, rates):
    if not date:
        return ""

    rate_instance = rates.get(date.isoformat())

    if not rate_instance:
        return _("No exchange rate found")

    return rate_instance.rate


@register.simple_tag
def calcualte_profit_or_loss_in_local_currency(model, open_rate, close_rate):
    return (
        round(model["close_amount"] * close_rate, 2)
        - round(model["open_amount"] * open_rate, 2)
        if model["close_amount"]
        else None
    )


@register.filter
def to_local_currency(value, rate):
    return value * rate if rate and value else None

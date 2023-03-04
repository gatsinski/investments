from django import template

register = template.Library()


@register.filter
def calculate_tax(value, percentage=10):
    return (
        value.get("gross_amount") * percentage / 100
        if not value.get("total_withheld_tax")
        else 0
    )


@register.simple_tag
def calculate_aggregated_tax(value, percentage=10):
    return value * percentage / 100

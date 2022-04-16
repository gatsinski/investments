from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from investments import chart_constants


def get_chart_data(queryset, label, colors, label_map=None):
    if label_map:
        labels = [label_map[report["label"]] for report in queryset]
    else:
        labels = [report["label"] for report in queryset]

    datasets = [
        {
            "label": label,
            "data": [report["value"] for report in queryset],
            "backgroundColor": colors,
        }
    ]

    return {"labels": labels, "datasets": datasets}


def get_all_days(queryset):
    first_date = datetime.strptime(queryset.first()["label"], "%d.%m.%Y").date()
    last_date = datetime.strptime(queryset.last()["label"], "%d.%m.%Y").date()

    delta = last_date - first_date

    days = {}

    for i in range(delta.days + 1):
        date = first_date + timedelta(days=i)

        days[f"{date.day}.{date.month}.{date.year}"] = None

    return days


def get_all_months(queryset):
    first_date = datetime.strptime(queryset.first()["label"], "%m.%Y").date()
    last_date = datetime.strptime(queryset.last()["label"], "%m.%Y").date()

    delta = relativedelta(last_date, first_date)

    months_difference = (delta.years * 12) + delta.months

    months = {}

    for i in range(months_difference + 1):
        date = first_date + relativedelta(months=i)

        months[f"{date.month}.{date.year}"] = None

    return months


def get_all_quarters(queryset):
    first_date_quarter, first_date_year = queryset.first()["label"].split("/")
    first_date_string = f"{int(first_date_quarter) * 3}.{first_date_year}"
    first_date = datetime.strptime(first_date_string, "%m.%Y").date()

    last_date_quarter, last_date_year = queryset.last()["label"].split("/")
    last_date_string = f"{int(last_date_quarter) * 3}.{last_date_year}"
    last_date = datetime.strptime(last_date_string, "%m.%Y").date()

    delta = relativedelta(last_date, first_date)

    months_difference = (delta.years * 12) + delta.months
    quarters_difference = months_difference // 3

    quarters = {}

    for i in range(quarters_difference + 1):
        date = first_date + relativedelta(months=i * 3)

        quarters[f"{date.month // 3}/{date.year}"] = None

    return quarters


def get_all_years(queryset):
    first_year = queryset.first()["label"]
    last_year = queryset.last()["label"]

    years_difference = last_year - first_year

    years = {}

    for i in range(years_difference + 1):
        years[first_year + i] = None

    return years


def get_color(index):
    color_index = index % len(chart_constants.COLORS)

    return chart_constants.COLORS[color_index]
